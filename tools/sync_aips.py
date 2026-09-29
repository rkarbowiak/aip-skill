#!/usr/bin/env python3
"""Sync Google AIPs from aip-dev/google.aip.dev into the skill's references.

Reads the upstream commit pinned in UPSTREAM, copies every approved AIP from
the configured scopes into references/aips/, rewrites cross-links so they
resolve locally, and regenerates the AIP index (references/index.md plus the
compact index block inside SKILL.md).

Usage:
  python tools/sync_aips.py                 # clone the pinned commit and sync
  python tools/sync_aips.py --source DIR    # use an existing upstream checkout
  python tools/sync_aips.py --update        # pin the latest upstream commit first
  python tools/sync_aips.py --check         # fail if the output would change

Standard library only.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
UPSTREAM_FILE = REPO_ROOT / "UPSTREAM"
UPSTREAM_URL = "https://github.com/aip-dev/google.aip.dev.git"
SKILL_DIR = REPO_ROOT / "plugins" / "aip" / "skills" / "aip"
AIPS_DIR = SKILL_DIR / "references" / "aips"
INDEX_FILE = SKILL_DIR / "references" / "index.md"
SKILL_FILE = SKILL_DIR / "SKILL.md"

SITE = "https://google.aip.dev"
# Only the general scope for now. Other scopes (client-libraries, cloud, ...)
# use four-digit ids and could be added here.
SCOPES = ["general"]
INCLUDED_STATES = {"approved"}
# AIPs about the AIP process itself: kept in the index but not worth loading
# when designing an API.
PROCESS_CATEGORIES = {"meta", "process"}
TOC_MIN_LINES = 100

INDEX_BEGIN = "<!-- BEGIN GENERATED INDEX (tools/sync_aips.py) -->"
INDEX_END = "<!-- END GENERATED INDEX -->"


@dataclass
class Aip:
    id: int
    scope: str
    state: str
    category: str
    order: int
    title: str
    body: str
    summary: str = ""
    filename: str = ""

    @property
    def url(self) -> str:
        return f"{SITE}/{self.id}" if self.scope == "general" else f"{SITE}/{self.scope}/{self.id}"


# ---------------------------------------------------------------- parsing


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    """Parse the small YAML subset used by AIP front matter (no dependency on PyYAML)."""
    if not text.startswith("---"):
        raise ValueError("missing front matter")
    end = text.index("\n---", 3)
    raw, body = text[3:end], text[end + 4 :]
    data: dict[str, str] = {}
    parent = ""
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("- "):
            continue
        indent = len(line) - len(line.lstrip())
        key, _, value = line.strip().partition(":")
        value = value.strip().strip("'\"")
        if indent == 0:
            parent = key
            data[key] = value
        else:
            data[f"{parent}.{key}"] = value
    return data, body.lstrip("\n")


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:50].rstrip("-")


def github_anchor(heading: str) -> str:
    """Anchor the way GitHub renders it: lowercase, drop punctuation, spaces to dashes."""
    text = re.sub(r"`|\*|_", "", heading).strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def plain_text(markdown: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\[[^\]]*\]", r"\1", markdown)  # [text][ref]
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)  # [text](url)
    text = re.sub(r"\[([^\]]+)\]", r"\1", text)  # [text]
    text = re.sub(r"[*`]|(?<!\w)_|_(?!\w)", "", text)
    return " ".join(text.split())


def first_sentence(body: str) -> str:
    """First sentence of the first prose paragraph, used as the index summary."""
    body = re.sub(r"^\s*```.*?^\s*```", "", body, flags=re.DOTALL | re.MULTILINE)
    for para in re.split(r"\n\s*\n", body):
        if para.lstrip("\n").startswith(("    ", "\t")):
            continue  # indented code block or list continuation
        para = para.strip()
        para = re.sub(r"^\d+\.\s+", "", para)  # a numbered rule reads fine on its own
        if not para or para.startswith(("#", "|", "<", "[", "-", "*", ">")):
            continue
        text = plain_text(para)
        match = re.match(r"(.+?(?<!e\.g)(?<!i\.e)[.!?])(\s|$)", text)
        sentence = match.group(1) if match else text
        return sentence if len(sentence) <= 220 else sentence[:217].rstrip() + "..."
    return ""


def summarize(body: str) -> str:
    """Prefer the first normative sentence under "## Guidance"; fall back to the intro."""
    guidance = re.split(r"^## Guidance\s*$", body, maxsplit=1, flags=re.MULTILINE)
    if len(guidance) == 2:
        section = re.split(r"^## ", guidance[1], maxsplit=1, flags=re.MULTILINE)[0]
        sentence = first_sentence(section)
        # Skip sentences that lean on the intro, such as "These masks are called ...".
        if sentence and not sentence.endswith(":") and not re.match(r"(This|These|It)\b", sentence):
            return sentence
    return first_sentence(body)


def load_aips(source: Path) -> list[Aip]:
    aips = []
    for scope in SCOPES:
        for path in sorted((source / "aip" / scope).glob("*.md")):
            meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
            title_match = re.match(r"#\s+(.+)\n", body)
            if not title_match:
                raise ValueError(f"{path}: no title heading")
            aip = Aip(
                id=int(meta["id"]),
                scope=scope,
                state=meta.get("state", ""),
                category=meta.get("placement.category", "misc"),
                order=int(meta.get("placement.order", "0") or 0),
                title=title_match.group(1).strip(),
                body=body[title_match.end() :].lstrip("\n"),
            )
            aip.summary = summarize(aip.body)
            aip.filename = f"{aip.id:04d}-{slugify(aip.title)}.md"
            aips.append(aip)
    return aips


def load_categories(source: Path) -> dict[str, str]:
    """Category code -> display title, in upstream order."""
    categories: dict[str, str] = {}
    code = ""
    for line in (source / "aip" / "general" / "scope.yaml").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*- code:\s*(\S+)", line)
        if m:
            code = m.group(1)
            categories[code] = code.replace("-", " ").title()
            continue
        m = re.match(r"\s+title:\s*(.+)", line)
        if m and code:
            categories[code] = m.group(1).strip()
    return categories


# ---------------------------------------------------------------- rewriting

# Link targets that point at another AIP, in every spelling upstream uses:
# ./0158.md  ./0158  ../0180.md  /158  https://aip.dev/158  https://google.aip.dev/158
AIP_TARGET = re.compile(
    r"^(?:\.{1,2}/|/|https?://(?:google\.)?aip\.dev/)(?:general/)?0*(\d{1,4})(?:\.md)?(#[\w\-]+)?$"
)


def rewrite_target(target: str, local: dict[int, Aip]) -> str:
    m = AIP_TARGET.match(target)
    if m:
        number, anchor = int(m.group(1)), m.group(2) or ""
        if number in local:
            return local[number].filename + anchor
        return f"{SITE}/{number}{anchor}"
    if target.startswith("/"):
        return SITE + target  # site-relative asset or the index page
    return target


def rewrite_links(body: str, local: dict[int, Aip]) -> str:
    # Reference definitions: "[label]: target"
    body = re.sub(
        r"^(\s*\[[^\]]+\]:\s+)(\S+)",
        lambda m: m.group(1) + rewrite_target(m.group(2), local),
        body,
        flags=re.MULTILINE,
    )
    # Inline links: "[text](target)"
    body = re.sub(
        r"(\]\()([^)\s]+)(\))",
        lambda m: m.group(1) + rewrite_target(m.group(2), local) + m.group(3),
        body,
    )
    return body


def headings_outside_code(body: str, max_level: int = 6) -> list[tuple[int, str]]:
    result, in_fence = [], False
    for line in body.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        m = re.match(rf"(#{{2,{max_level}}})\s+(.+)", line)
        if m and not in_fence:
            result.append((len(m.group(1)), m.group(2).strip()))
    return result


def render_aip(aip: Aip, local: dict[int, Aip], commit: str) -> str:
    body = rewrite_links(aip.body, local).rstrip() + "\n"
    lines = [
        f"# AIP-{aip.id}: {aip.title}",
        "",
        f"> Source: <{aip.url}> (state: {aip.state}, category: {aip.category}).",
        f"> Copied from aip-dev/google.aip.dev@{commit[:12]} under CC BY 4.0 (text) and",
        "> Apache 2.0 (code samples). Changes: front matter removed, title prefixed,",
        "> contents list added, links rewritten to local files.",
        "",
    ]
    if body.count("\n") >= TOC_MIN_LINES:
        lines.append("Contents:")
        lines.append("")
        for level, heading in headings_outside_code(body, max_level=4):
            indent = "  " * (level - 2)
            lines.append(f"{indent}- [{plain_text(heading)}](#{github_anchor(heading)})")
        lines.append("")
    return "\n".join(lines) + "\n" + body


def check_links(docs: dict[str, str]) -> list[str]:
    """Report links between bundled AIPs whose file or anchor does not exist."""
    anchors = {
        name: {github_anchor(h) for _, h in headings_outside_code(text)} for name, text in docs.items()
    }
    problems = []
    for name, text in docs.items():
        prose = re.sub(r"```.*?```|`[^`\n]*`", "", text, flags=re.DOTALL)
        targets = re.findall(r"\]\(([^)\s]+)\)", prose) + re.findall(r"^\s*\[[^\]]+\]:\s+(\S+)", prose, re.M)
        for target in targets:
            if re.match(r"[a-z]+:", target):
                continue
            file, _, anchor = target.partition("#")
            file = file or name
            if file not in docs:
                problems.append(f"{name}: link to missing file {target}")
            elif anchor and anchor not in anchors[file]:
                problems.append(f"{name}: link to missing anchor {target} (upstream issue)")
    return sorted(set(problems))


# ---------------------------------------------------------------- index


def render_index(aips: list[Aip], categories: dict[str, str], commit: str) -> str:
    out = [
        "# AIP index",
        "",
        f"All approved general AIPs bundled with this skill (upstream commit {commit[:12]}),",
        "grouped the way <https://google.aip.dev/general> groups them. Each entry links to",
        "the local copy and quotes the first sentence of its guidance.",
        "",
    ]
    for code, title in categories.items():
        group = sorted((a for a in aips if a.category == code), key=lambda a: (a.order, a.id))
        if not group:
            continue
        out += [f"## {title}", ""]
        for a in group:
            out.append(f"- [AIP-{a.id}: {a.title}](aips/{a.filename}): {a.summary}")
        out.append("")
    return "\n".join(out)


def render_skill_block(aips: list[Aip], categories: dict[str, str]) -> str:
    out = [INDEX_BEGIN, ""]
    for code, title in categories.items():
        if code in PROCESS_CATEGORIES:
            continue
        group = sorted((a for a in aips if a.category == code), key=lambda a: (a.order, a.id))
        if not group:
            continue
        items = ", ".join(f"{a.id} {a.title}" for a in group)
        out.append(f"- **{title}**: {items}")
    out += ["", INDEX_END]
    return "\n".join(out)


# ---------------------------------------------------------------- main


def git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def checkout(commit: str, dest: Path) -> None:
    git("init", "-q", str(dest))
    git("remote", "add", "origin", UPSTREAM_URL, cwd=dest)
    git("fetch", "-q", "--depth", "1", "origin", commit, cwd=dest)
    git("checkout", "-q", "FETCH_HEAD", cwd=dest)


def build(source: Path, commit: str) -> dict[Path, str]:
    """Return every generated file and its content (SKILL.md included)."""
    all_aips = load_aips(source)
    aips = [a for a in all_aips if a.state in INCLUDED_STATES]
    local = {a.id: a for a in aips}
    categories = load_categories(source)
    unknown = {a.category for a in aips} - set(categories)
    if unknown:
        raise ValueError(f"categories missing from scope.yaml: {unknown}")

    files = {AIPS_DIR / a.filename: render_aip(a, local, commit) for a in aips}
    files[INDEX_FILE] = render_index(aips, categories, commit)

    skill = SKILL_FILE.read_text(encoding="utf-8")
    if INDEX_BEGIN not in skill or INDEX_END not in skill:
        raise ValueError(f"{SKILL_FILE} lacks the generated index markers")
    head, rest = skill.split(INDEX_BEGIN, 1)
    tail = rest.split(INDEX_END, 1)[1]
    files[SKILL_FILE] = head + render_skill_block(aips, categories) + tail

    for problem in check_links({p.name: t for p, t in files.items() if p.parent == AIPS_DIR}):
        print(f"warning: {problem}", file=sys.stderr)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, help="existing google.aip.dev checkout (skips cloning)")
    parser.add_argument("--update", action="store_true", help="pin the latest upstream commit before syncing")
    parser.add_argument("--check", action="store_true", help="exit 1 if the generated files are out of date")
    args = parser.parse_args()

    if args.update:
        head = git("ls-remote", UPSTREAM_URL, "HEAD").split()[0]
        UPSTREAM_FILE.write_text(head + "\n", encoding="utf-8")
    commit = UPSTREAM_FILE.read_text(encoding="utf-8").strip()

    with tempfile.TemporaryDirectory() as tmp:
        source = args.source
        if source is None:
            source = Path(tmp) / "upstream"
            checkout(commit, source)
        else:
            actual = git("rev-parse", "HEAD", cwd=source)
            if actual != commit:
                print(f"warning: --source is at {actual[:12]}, UPSTREAM pins {commit[:12]}", file=sys.stderr)
        files = build(source, commit)

    stale = {p for p in AIPS_DIR.glob("*.md")} - set(files)
    changed = [p for p, t in files.items() if not p.exists() or p.read_text(encoding="utf-8") != t]

    if args.check:
        for p in sorted(changed) + sorted(stale):
            print(f"out of date: {p.relative_to(REPO_ROOT)}")
        return 1 if changed or stale else 0

    AIPS_DIR.mkdir(parents=True, exist_ok=True)
    for p in stale:
        p.unlink()
    for p in changed:
        p.write_text(files[p], encoding="utf-8", newline="\n")
    aip_count = len(files) - 2
    print(f"synced {aip_count} AIPs at {commit[:12]}: {len(changed)} written, {len(stale)} removed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
