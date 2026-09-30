"""Tests for the api-linter wrapper. Run with: python -m unittest discover -s tests

The end-to-end tests need api-linter (and network access for the first
googleapis fetch); they are skipped when api-linter isn't installed.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "plugins" / "aip" / "skills" / "aip" / "scripts"
LINT = SCRIPTS / "lint.py"
EXAMPLES = REPO / "plugins" / "aip" / "skills" / "aip" / "references" / "examples"
BAD = REPO / "tests" / "fixtures" / "bad.proto"

sys.path.insert(0, str(SCRIPTS))
import lint  # noqa: E402

try:
    lint.find_linter()
    HAVE_LINTER = True
except lint.SetupError:
    HAVE_LINTER = False


def run(*args: str, cwd: Path = REPO, env: dict | None = None) -> subprocess.CompletedProcess:
    full_env = None if env is None else {**os.environ, **env}
    return subprocess.run([sys.executable, str(LINT), *args], cwd=cwd, capture_output=True, text=True, env=full_env)


class References(unittest.TestCase):
    def test_core_rule_points_at_bundled_aip(self):
        label, reference = lint.aip_reference("core::0158::request-page-size-field")
        self.assertEqual(label, "AIP-158")
        self.assertTrue(reference.replace("\\", "/").endswith("references/aips/0158-pagination.md"))

    def test_other_scopes_point_at_the_site(self):
        self.assertEqual(
            lint.aip_reference("client-libraries::4232::repeated-fields"),
            ("AIP-4232", "https://google.aip.dev/client-libraries/4232"),
        )

    def test_unknown_rule(self):
        self.assertEqual(lint.aip_reference("custom-rule"), (None, ""))


class ImportRoot(unittest.TestCase):
    def test_package_path_and_flat_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            nested = Path(tmp, "proto", "library", "v1", "book.proto")
            nested.parent.mkdir(parents=True)
            nested.write_text('syntax = "proto3";\npackage library.v1;\n')
            flat = Path(tmp, "flat.proto")
            flat.write_text('syntax = "proto3";\npackage library.v1;\n')
            self.assertEqual(lint.import_root(nested), Path(tmp, "proto"))
            self.assertEqual(lint.import_root(flat), Path(tmp))


@unittest.skipUnless(HAVE_LINTER, "api-linter not installed")
class EndToEnd(unittest.TestCase):
    def test_example_is_clean(self):
        result = run(str(EXAMPLES))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("0 finding(s)", result.stdout)

    def test_bad_fixture_has_findings_with_cwd_relative_paths(self):
        result = run(str(BAD))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("AIP-158", result.stdout)
        self.assertIn("tests" + ("\\" if sys.platform == "win32" else "/") + "fixtures", result.stdout)

    def test_missing_path_is_a_setup_error(self):
        self.assertEqual(run("does/not/exist.proto").returncode, 2)

    def test_same_file_name_in_two_roots_is_linted_twice(self):
        with tempfile.TemporaryDirectory() as tmp:
            for folder, package, message in [("a", "foo.v1", "Alpha"), ("b", "bar.v1", "Beta")]:
                path = Path(tmp, folder, "service.proto")
                path.parent.mkdir()
                path.write_text(f'syntax = "proto3";\npackage {package};\nmessage {message} {{ string x = 1; }}\n')
            result = run(tmp, "--json")
            self.assertEqual(result.returncode, 1, result.stderr)
            reports = json.loads(result.stdout)
            paths = sorted(Path(r["file_path"]).parent.name for r in reports)
            self.assertEqual(paths, ["a", "b"])
            messages = json.dumps(reports)
            self.assertIn("Alpha", messages)
            self.assertIn("Beta", messages)

    def test_partially_vendored_googleapis_falls_back_to_cache(self):
        cache = lint.cache_dir() / "googleapis"
        if not (cache / lint.COMPLETE_MARKER).is_file():
            self.assertEqual(run(str(EXAMPLES)).returncode, 0)  # populates the cache
        with tempfile.TemporaryDirectory() as tmp:
            vendored = Path(tmp, "third_party", "google", "api")
            vendored.mkdir(parents=True)
            for name in ("annotations.proto", "http.proto"):
                shutil.copy(cache / "google" / "api" / name, vendored / name)
            shutil.copytree(EXAMPLES / "library", Path(tmp, "proto", "library"))
            result = run(str(Path(tmp, "proto")), "-I", str(Path(tmp, "third_party")))
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_fresh_cache_is_fetched_for_a_transitive_google_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp, "proto", "library", "v1")
            root.mkdir(parents=True)
            (root / "common.proto").write_text(
                textwrap.dedent(
                    """\
                    syntax = "proto3";
                    package library.v1;
                    import "google/api/field_behavior.proto";
                    message Common { string x = 1 [(google.api.field_behavior) = OPTIONAL]; }
                    """
                )
            )
            (root / "book.proto").write_text(
                textwrap.dedent(
                    """\
                    syntax = "proto3";
                    package library.v1;
                    import "library/v1/common.proto";
                    message Book { Common common = 1; }
                    """
                )
            )
            env = {"XDG_CACHE_HOME": str(Path(tmp, "cache")), "CLAUDE_PLUGIN_DATA": ""}
            result = run(str(root / "book.proto"), env=env)
            self.assertIn(result.returncode, (0, 1), result.stderr + result.stdout)
            self.assertTrue(Path(tmp, "cache", "aip-skill", "googleapis", lint.COMPLETE_MARKER).is_file())

    def test_config_is_found_in_a_parent_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, ".git").mkdir()
            Path(tmp, "api-linter.yaml").write_text(
                textwrap.dedent(
                    """\
                    - disabled_rules:
                        - core::0192::has-comments
                    """
                )
            )
            proto = Path(tmp, "proto", "x.proto")
            proto.parent.mkdir()
            proto.write_text('syntax = "proto3";\npackage x.v1;\nmessage Thing { string x = 1; }\n')
            result = run(str(proto), cwd=Path(tmp, "proto"))
            self.assertIn("config:", result.stdout)
            self.assertNotIn("core::0192::has-comments", result.stdout)


if __name__ == "__main__":
    unittest.main()
