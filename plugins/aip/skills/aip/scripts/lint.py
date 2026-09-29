#!/usr/bin/env python3
"""Lint .proto files against the AIPs with googleapis/api-linter.

Usage:
  python lint.py PATH [PATH ...] [-I DIR ...] [--config FILE]
                 [--disable-rule RULE ...] [--json]

PATH can be a .proto file or a directory (searched recursively, skipping
google/ and vendored third_party/ trees).

What it does on top of plain api-linter:
  * finds api-linter on PATH or in $(go env GOPATH)/bin, and explains how to
    install it when missing;
  * works out import roots from each file's `package` line and any buf.yaml;
  * fetches the googleapis common protos (google/api, rpc, type, longrunning)
    into a cache the first time they are needed;
  * groups findings by AIP and points at the bundled copy of each AIP.

Exit status: 0 no findings, 1 findings, 2 setup or compile error.
Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
AIPS_DIR = SKILL_DIR / "references" / "aips"
GOOGLEAPIS_URL = "https://github.com/googleapis/googleapis.git"
GOOGLEAPIS_DIRS = ["google/api", "google/rpc", "google/type", "google/longrunning"]
CONFIG_NAMES = ["api-linter.yaml", ".api-linter.yaml", "api-linter.json", ".api-linter.json"]
SKIP_DIRS = {".git", "node_modules", "third_party", "vendor", "google"}

INSTALL_HELP = """\
api-linter is not installed. Install it with one of:
  go install github.com/googleapis/api-linter/v2/cmd/api-linter@latest
  (or download a binary from https://github.com/googleapis/api-linter/releases
   and put it on PATH)
Then re-run this script. Without it, review the proto by hand against the
bundled AIPs."""


def fail(message: str) -> "NoReturn":  # type: ignore[name-defined]
    print(message, file=sys.stderr)
    sys.exit(2)


def find_linter() -> str:
    found = shutil.which("api-linter")
    if found:
        return found
    go = shutil.which("go")
    if go:
        gopath = subprocess.run([go, "env", "GOPATH"], capture_output=True, text=True).stdout.strip()
        for name in ("api-linter", "api-linter.exe"):
            candidate = Path(gopath) / "bin" / name
            if candidate.is_file():
                return str(candidate)
    fail(INSTALL_HELP)


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
            fail(f"not a .proto file or directory: {raw}")
    if not files:
        fail("no .proto files found")
    return sorted(set(files))


def import_root(proto: Path) -> Path:
    """Directory that imports of this file are relative to.

    For proto/agenda/v1/talk.proto with `package agenda.v1;` that is proto/.
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


def cache_dir() -> Path:
    base = os.environ.get("CLAUDE_PLUGIN_DATA") or os.environ.get("XDG_CACHE_HOME")
    if base:
        return Path(base) / "aip-skill"
    return Path.home() / ".cache" / "aip-skill"


def googleapis_include(includes: list[Path]) -> Path | None:
    """Return a directory providing google/api/*.proto, fetching it if needed."""
    for directory in includes:
        if (directory / "google" / "api" / "annotations.proto").is_file():
            return None  # the project already vendors them
    target = cache_dir() / "googleapis"
    if (target / "google" / "api" / "annotations.proto").is_file():
        return target
    if not shutil.which("git"):
        fail("git is needed to fetch the googleapis common protos; or pass -I DIR pointing at a googleapis checkout")
    print(f"fetching googleapis common protos into {target} (one time)...", file=sys.stderr)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name("googleapis.tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    steps = [
        ["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--sparse", GOOGLEAPIS_URL, str(tmp)],
        ["git", "-C", str(tmp), "sparse-checkout", "set", "--no-cone", *[f"/{d}/*" for d in GOOGLEAPIS_DIRS]],
    ]
    for step in steps:
        result = subprocess.run(step, capture_output=True, text=True)
        if result.returncode != 0:
            shutil.rmtree(tmp, ignore_errors=True)
            fail(f"failed to fetch googleapis protos: {result.stderr.strip()}")
    shutil.rmtree(target, ignore_errors=True)
    tmp.rename(target)
    return target


def find_config(roots: list[Path]) -> Path | None:
    for directory in [Path.cwd(), *roots]:
        for name in CONFIG_NAMES:
            if (directory / name).is_file():
                return directory / name
    return None


def aip_reference(rule_id: str) -> tuple[int | None, str]:
    match = re.match(r"\w+::(\d+)::", rule_id)
    if not match:
        return None, ""
    number = int(match.group(1))
    local = next(AIPS_DIR.glob(f"{number:04d}-*.md"), None)
    return number, (str(local) if local else f"https://google.aip.dev/{number}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint .proto files against the AIPs.")
    parser.add_argument("paths", nargs="+", help=".proto files or directories")
    parser.add_argument("-I", "--proto-path", action="append", default=[], help="extra import directory")
    parser.add_argument("--config", help="api-linter config file (auto-detected if omitted)")
    parser.add_argument("--disable-rule", action="append", default=[], help="rule to disable, e.g. core::0191::java-package")
    parser.add_argument("--json", action="store_true", help="print api-linter's raw JSON")
    args = parser.parse_args()

    linter = find_linter()
    protos = collect_protos(args.paths)
    roots = list(dict.fromkeys([import_root(p) for p in protos]))
    includes = [Path(p).resolve() for p in args.proto_path] + roots
    extra = googleapis_include(includes)
    if extra:
        includes.append(extra)

    # api-linter resolves the files to lint through the import paths, so pass
    # each file relative to its own import root (all roots are in -I).
    cwd = roots[0]
    targets = [p.relative_to(import_root(p)).as_posix() for p in protos]
    command = [linter, "--output-format", "json"]
    for directory in includes:
        command += ["-I", str(directory)]
    config = Path(args.config) if args.config else find_config(roots)
    if config:
        command += ["--config", str(config.resolve())]
    for rule in args.disable_rule:
        command += ["--disable-rule", rule]
    command += targets

    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    try:
        report = json.loads(result.stdout or "null")
    except json.JSONDecodeError:
        report = None
    if report is None:
        fail(f"api-linter failed (exit {result.returncode}):\n{result.stderr.strip() or result.stdout.strip()}")

    if args.json:
        print(json.dumps(report, indent=2))
        return 1 if any(f.get("problems") for f in report) else 0

    by_aip: dict[int | None, list[tuple[str, int, str]]] = defaultdict(list)
    references: dict[int | None, str] = {}
    total = 0
    for file_report in report:
        for problem in file_report.get("problems") or []:
            total += 1
            rule = problem.get("rule_id", "?")
            number, reference = aip_reference(rule)
            references[number] = reference
            start = problem.get("location", {}).get("start_position", {})
            line, column = start.get("line_number", 0), start.get("column_number", 0)
            where = f"{file_report.get('file_path')}:{line}:{column}"
            by_aip[number].append((file_report.get("file_path", ""), line, f"  {where}  {rule}\n    {problem.get('message', '').strip()}"))

    if config:
        print(f"config: {config}")
    print(f"linted {len(protos)} file(s) with {Path(linter).name}; {total} finding(s)")
    for number in sorted(by_aip, key=lambda n: (n is None, n or 0)):
        heading = f"AIP-{number}" if number is not None else "Other rules"
        print(f"\n{heading} ({len(by_aip[number])})  ->  {references.get(number) or '-'}")
        print("\n".join(text for _, _, text in sorted(by_aip[number])))
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
