#!/usr/bin/env python3
"""Lint .proto files against the AIPs with googleapis/api-linter.

Usage:
  python3 lint.py PATH [PATH ...] [-I DIR ...] [--config FILE]
                  [--disable-rule RULE ...] [--json]

PATH can be a .proto file or a directory (searched recursively, skipping
google/, third_party/, vendor/ and hidden directories).

What it does on top of plain api-linter:
  * finds api-linter on PATH, in $GOBIN or in $(go env GOPATH)/bin, and
    explains how to install it when missing;
  * works out each file's import root from its `package` line (or the nearest
    buf.yaml) and lints every root separately, so files with the same relative
    path in different roots are each linted exactly once;
  * fetches the googleapis common protos (google/api, rpc, type, longrunning)
    into a cache when an import needs them, and keeps them as the last import
    path so a partially vendored copy still works;
  * finds an api-linter config in the current directory, the import roots, or
    their parents up to the repository root;
  * prints findings grouped by AIP with paths relative to the current
    directory and the bundled copy of each AIP to read.

Exit status: 0 no findings, 1 findings, 2 setup or compile error.
Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
AIPS_DIR = SKILL_DIR / "references" / "aips"
SITE = "https://google.aip.dev"
GOOGLEAPIS_URL = "https://github.com/googleapis/googleapis.git"
GOOGLEAPIS_DIRS = ["google/api", "google/rpc", "google/type", "google/longrunning"]
COMPLETE_MARKER = ".aip-skill-complete"
CONFIG_NAMES = ["api-linter.yaml", ".api-linter.yaml", "api-linter.json", ".api-linter.json"]
SKIP_DIRS = {"node_modules", "third_party", "vendor", "google"}
IMPORT_RE = re.compile(r'^\s*import\s+(?:public\s+|weak\s+)?"([^"]+)"\s*;', re.MULTILINE)

INSTALL_HELP = """\
api-linter is not installed. Install it with one of:
  go install github.com/googleapis/api-linter/v2/cmd/api-linter@latest
  (or download a binary from https://github.com/googleapis/api-linter/releases
   and put it on PATH)
Then re-run this script. Without it, review the proto by hand against the
bundled AIPs."""


class SetupError(Exception):
    """A problem that stops linting; reported with exit status 2."""


# ---------------------------------------------------------------- discovery


def find_linter() -> str:
    found = shutil.which("api-linter")
    if found:
        return found
    candidates: list[Path] = []
    if os.environ.get("GOBIN"):
        candidates.append(Path(os.environ["GOBIN"]))
    go = shutil.which("go")
    if go:
        env = subprocess.run([go, "env", "GOBIN", "GOPATH"], capture_output=True, text=True).stdout.splitlines()
        gobin, gopath = (env + ["", ""])[:2]
        if gobin.strip():
            candidates.append(Path(gobin.strip()))
        candidates += [Path(p) / "bin" for p in gopath.strip().split(os.pathsep) if p]
    for directory in candidates:
        for name in ("api-linter", "api-linter.exe"):
            if (directory / name).is_file():
                return str(directory / name)
    raise SetupError(INSTALL_HELP)


def collect_protos(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        path = Path(raw).resolve()
        if path.is_file() and path.suffix == ".proto":
            files.append(path)
        elif path.is_dir():
            for root, dirs, names in os.walk(path):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
                files += [Path(root) / n for n in names if n.endswith(".proto")]
        else:
            raise SetupError(f"not a .proto file or directory: {raw}")
    if not files:
        raise SetupError("no .proto files found")
    return sorted(set(files))


def import_root(proto: Path) -> Path:
    """Directory that imports of this file are relative to.

    For proto/library/v1/book.proto with `package library.v1;` that is proto/.
    Falls back to the nearest buf.yaml, then to the file's own directory.
    """
    text = proto.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"^\s*package\s+([\w.]+)\s*;", text, re.MULTILINE)
    if match:
        parts = match.group(1).split(".")
        parent = proto.parent
        if [p.lower() for p in parent.parts[-len(parts) :]] == [p.lower() for p in parts]:
            return Path(*parent.parts[: -len(parts)])
    for directory in proto.parents:
        if (directory / "buf.yaml").is_file():
            return directory
    return proto.parent


def find_config(roots: list[Path]) -> Path | None:
    """First api-linter config next to the linted files or in the cwd.

    Each start directory is searched upwards until a .git directory or the
    home directory, whichever comes first.
    """
    home = Path.home().resolve()
    for start in [*roots, Path.cwd().resolve()]:
        for directory in [start, *start.parents]:
            for name in CONFIG_NAMES:
                if (directory / name).is_file():
                    return directory / name
            if (directory / ".git").exists() or directory == home:
                break
    return None


def display(path: Path) -> str:
    """Path relative to the cwd when it is inside it, absolute otherwise."""
    try:
        relative = os.path.relpath(path)
    except ValueError:  # another drive on Windows
        return str(path)
    return str(path) if relative.startswith("..") else relative


# ---------------------------------------------------------------- googleapis


def cache_dir() -> Path:
    base = os.environ.get("CLAUDE_PLUGIN_DATA") or os.environ.get("XDG_CACHE_HOME")
    if base:
        return Path(base) / "aip-skill"
    return Path.home() / ".cache" / "aip-skill"


def remove_tree(path: Path) -> None:
    """rmtree that also removes read-only files (git pack files on Windows)."""

    def clear_and_retry(func, target, _exc):
        os.chmod(target, stat.S_IWRITE)
        func(target)

    if not path.exists():
        return
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=clear_and_retry)
    else:
        shutil.rmtree(path, onerror=clear_and_retry)


def fetch_googleapis(target: Path) -> None:
    if not shutil.which("git"):
        raise SetupError(
            "git is needed to fetch the googleapis common protos; "
            "or pass -I DIR pointing at a googleapis checkout"
        )
    print(f"fetching googleapis common protos into {target} (one time)...", file=sys.stderr)
    target.parent.mkdir(parents=True, exist_ok=True)
    for leftover in target.parent.glob("googleapis-*"):  # from runs that were killed
        if time.time() - leftover.stat().st_mtime > 3600:
            remove_tree(leftover)
    tmp = Path(tempfile.mkdtemp(prefix="googleapis-", dir=target.parent))
    try:
        steps = [
            ["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--sparse", GOOGLEAPIS_URL, str(tmp / "src")],
            ["git", "-C", str(tmp / "src"), "sparse-checkout", "set", "--no-cone", *[f"/{d}/*" for d in GOOGLEAPIS_DIRS]],
        ]
        for step in steps:
            result = subprocess.run(step, capture_output=True, text=True)
            if result.returncode != 0:
                raise SetupError(f"failed to fetch googleapis protos: {result.stderr.strip()}")
        remove_tree(tmp / "src" / ".git")
        (tmp / "src" / COMPLETE_MARKER).write_text("ok\n", encoding="utf-8")
        if (target / COMPLETE_MARKER).is_file():
            return  # another run finished first; keep its copy
        try:
            remove_tree(target)
            os.replace(tmp / "src", target)
        except OSError:
            if not (target / COMPLETE_MARKER).is_file():
                raise
    finally:
        remove_tree(tmp)


def unresolved_google_imports(protos: list[Path], includes: list[Path]) -> set[str]:
    """google/ imports (other than well-known types) that no include directory provides.

    Follows imports transitively through the project and any vendored google/
    files, so an import two levels down, or a vendored file whose own
    dependencies are missing, still counts.
    """
    missing: set[str] = set()
    seen: set[Path] = set()
    queue = list(protos)
    while queue:
        proto = queue.pop()
        if proto in seen:
            continue
        seen.add(proto)
        for name in IMPORT_RE.findall(proto.read_text(encoding="utf-8", errors="replace")):
            if name.startswith("google/protobuf/"):
                continue  # built into api-linter
            found = next((d / name for d in includes if (d / name).is_file()), None)
            if found:
                queue.append(found)
            elif name.startswith("google/"):
                missing.add(name)
    return missing


def googleapis_include(protos: list[Path], includes: list[Path]) -> Path | None:
    """The cached googleapis directory, fetched if an import needs it.

    The cache is returned whenever it exists, even when the project vendors
    some of these files, so it fills the gaps as the last import path.
    """
    target = cache_dir() / "googleapis"
    if (target / COMPLETE_MARKER).is_file():
        return target
    legacy = (target / "google" / "api" / "annotations.proto").is_file()  # older lint.py, no marker
    if not unresolved_google_imports(protos, includes):
        return target if legacy else None
    try:
        fetch_googleapis(target)
    except SetupError:
        if legacy:
            return target
        raise
    return target


# ---------------------------------------------------------------- linting


def aip_reference(rule_id: str) -> tuple[str | None, str]:
    """('AIP-158', path or URL of the AIP) for a rule id like core::0158::..."""
    match = re.match(r"([\w-]+)::(\d+)::", rule_id)
    if not match:
        return None, ""
    scope, number = match.group(1), int(match.group(2))
    local = next(AIPS_DIR.glob(f"{number:04d}-*.md"), None) if scope == "core" else None
    if local:
        return f"AIP-{number}", str(local)
    url = f"{SITE}/{number}" if scope == "core" else f"{SITE}/{scope}/{number}"
    return f"AIP-{number}", url


def warn_about_config_paths(config: Path) -> None:
    text = config.read_text(encoding="utf-8", errors="replace")
    if re.search(r"(included|excluded)_paths", text):
        print(
            "note: api-linter matches included_paths/excluded_paths against paths relative to "
            "each file's import root (for example library/v1/book.proto), not to the config file",
            file=sys.stderr,
        )


def run_linter(linter: str, root: Path, files: list[Path], includes: list[Path], extra_args: list[str]) -> list[dict]:
    targets = [f.relative_to(root).as_posix() for f in files]
    command = [linter, "--output-format", "json"]
    for directory in includes:
        command += ["-I", str(directory)]
    command += extra_args + targets
    result = subprocess.run(command, cwd=root, capture_output=True, text=True)
    try:
        report = json.loads(result.stdout or "null")
    except json.JSONDecodeError:
        report = None
    if not isinstance(report, list):
        searched = "\n".join(f"  {d}" for d in includes)
        raise SetupError(
            f"api-linter failed (exit {result.returncode}):\n{result.stderr.strip() or result.stdout.strip()}\n"
            f"import paths searched, in order (the last one is the googleapis cache if present):\n{searched}\n"
            "A missing project import usually needs -I pointing at the directory its path is relative to."
        )
    for file_report in report:
        file_report["file_path"] = display(root / file_report.get("file_path", ""))
    return report


def lint(args: argparse.Namespace) -> int:
    linter = find_linter()
    protos = collect_protos(args.paths)
    by_root: dict[Path, list[Path]] = defaultdict(list)
    for proto in protos:
        by_root[import_root(proto)].append(proto)
    roots = list(by_root)
    user_includes = [Path(p).resolve() for p in args.proto_path]
    googleapis = googleapis_include(protos, user_includes + roots)

    config = Path(args.config).resolve() if args.config else find_config(roots)
    extra_args: list[str] = []
    if config:
        warn_about_config_paths(config)
        extra_args += ["--config", str(config)]
    for rule in args.disable_rule:
        extra_args += ["--disable-rule", rule]

    report: list[dict] = []
    for root, files in by_root.items():
        # This root first so its own files win, then the user's paths, the
        # other roots (for cross-root imports) and the cache as a fallback.
        includes = [root, *user_includes, *[r for r in roots if r != root]]
        if googleapis:
            includes.append(googleapis)
        report += run_linter(linter, root, files, list(dict.fromkeys(includes)), extra_args)

    total = sum(len(f.get("problems") or []) for f in report)
    if args.json:
        print(json.dumps(report, indent=2))
        return 1 if total else 0

    by_aip: dict[str | None, list[tuple[str, int, str]]] = defaultdict(list)
    references: dict[str | None, str] = {}
    for file_report in report:
        path = file_report["file_path"]
        for problem in file_report.get("problems") or []:
            rule = problem.get("rule_id", "?")
            label, reference = aip_reference(rule)
            references[label] = reference
            start = problem.get("location", {}).get("start_position", {})
            line, column = start.get("line_number", 0), start.get("column_number", 0)
            text = f"  {path}:{line}:{column}  {rule}\n    {problem.get('message', '').strip()}"
            by_aip[label].append((path, line, text))

    if config:
        print(f"config: {display(config)}")
    print(f"linted {len(protos)} file(s) with {Path(linter).name}; {total} finding(s)")
    for label in sorted(by_aip, key=lambda l: (l is None, int(l[4:]) if l else 0)):
        heading = label or "Other rules"
        print(f"\n{heading} ({len(by_aip[label])})  ->  {references.get(label) or '-'}")
        print("\n".join(text for _, _, text in sorted(by_aip[label])))
    return 1 if total else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint .proto files against the AIPs.")
    parser.add_argument("paths", nargs="+", help=".proto files or directories")
    parser.add_argument("-I", "--proto-path", action="append", default=[], help="extra import directory")
    parser.add_argument("--config", help="api-linter config file (auto-detected if omitted)")
    parser.add_argument("--disable-rule", action="append", default=[], help="rule to disable, e.g. core::0191::java-package")
    parser.add_argument("--json", action="store_true", help="print api-linter's JSON (paths relative to the cwd)")
    args = parser.parse_args()
    try:
        return lint(args)
    except SetupError as error:
        print(error, file=sys.stderr)
        return 2
    except Exception as error:  # anything unexpected must not look like "findings"
        print(f"lint.py: unexpected error: {error!r}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
