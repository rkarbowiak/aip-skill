# aip-skill

A Claude skill for designing and reviewing APIs against Google's
[API Improvement Proposals](https://google.aip.dev) (AIPs). It bundles every
approved general AIP, a quick reference of the rules people most often get
wrong, and a wrapper around [api-linter](https://linter.aip.dev) that groups
findings by AIP.

Unofficial. Not affiliated with or endorsed by Google.

## What it does

Ask Claude to design a gRPC service, review a `.proto` file, plan a change to a
shipped API, or explain an AIP, and the skill:

- reads the relevant AIPs from the bundled copies instead of relying on
  memory, and cites them (`AIP-158, must`);
- designs outside-in: resources and names, standard methods, fields, then
  patterns like pagination, field masks and long-running operations;
- runs api-linter when it's installed, then reviews what a linter can't see,
  such as the resource model, compatibility (AIP-180) and error handling;
- tells Google-specific conventions apart from general defects when the API
  isn't Google's.

## Install

### Claude Code (plugin)

```
/plugin marketplace add rkarbowiak/aip-skill
/plugin install aip@aip-skill
```

The skill is then available as `/aip:aip`, and Claude also loads it on its own
when a task involves API design.

### Claude Code (copy the skill only)

Copy `plugins/aip/skills/aip/` to `~/.claude/skills/aip/` (all projects) or to
`.claude/skills/aip/` in one repository.

### claude.ai

Zip the `plugins/aip/skills/aip/` folder and upload it under
Settings → Capabilities → Skills. The linter needs a shell, so on claude.ai the
skill reviews by reading the AIPs only.

### Optional: api-linter

```
go install github.com/googleapis/api-linter/v2/cmd/api-linter@latest
```

The lint script also needs Python 3 and git. On first run it downloads the
googleapis common protos (`google/api`, `google/rpc`, `google/type`,
`google/longrunning`, about 1 MB) into `~/.cache/aip-skill/`.

## Using the lint script directly

```
python3 plugins/aip/skills/aip/scripts/lint.py path/to/protos/
python3 plugins/aip/skills/aip/scripts/lint.py api/ -I third_party --disable-rule core::0191::java-package
```

Exit code 0 means clean, 1 means findings, 2 means a setup or compile error.

## Repository layout

```
.claude-plugin/marketplace.json   marketplace with one plugin
plugins/aip/
  .claude-plugin/plugin.json
  skills/aip/
    SKILL.md                      instructions + generated AIP index
    references/aips/              71 approved AIPs (generated)
    references/index.md           one-line summary per AIP (generated)
    references/examples/          lint-clean example API
    scripts/lint.py               api-linter wrapper
  evals/                          `claude plugin eval` suite
tools/sync_aips.py                regenerates references from upstream
tests/                            unit tests and lint fixtures
UPSTREAM                          pinned aip-dev/google.aip.dev commit
```

## Development

Everything under `references/aips/`, `references/index.md` and the index block
in `SKILL.md` is generated. Don't edit those by hand; change
`tools/sync_aips.py` instead.

```
python3 tools/sync_aips.py            # regenerate from the pinned commit
python3 tools/sync_aips.py --update   # sync from upstream HEAD, pin it if content changed
python3 tools/sync_aips.py --check    # CI: fail if generated files are stale
python3 -m unittest discover -s tests  # lint tests need api-linter
claude plugin validate . --strict
claude plugin eval ./plugins/aip     # runs model calls; costs money
```

A weekly GitHub Action syncs from upstream and opens a pull request when a
bundled AIP changed; it runs the tests before opening it. Pull requests opened
with the default `GITHUB_TOKEN` don't trigger CI, so either add a `SYNC_TOKEN`
secret (a fine-grained token with contents and pull-requests write) or allow
GitHub Actions to create pull requests in the repository settings. When a sync
lands, check whether the quick reference in `SKILL.md` needs updating.

## License

The skill, scripts and tooling are Apache 2.0 (see [LICENSE](LICENSE)); the
skill folder carries its own copy of LICENSE and NOTICE so it stays
attributed when copied on its own. The
bundled AIPs are © Google LLC, text under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) and code samples
under Apache 2.0; see [NOTICE](NOTICE) for the source and the changes made.
