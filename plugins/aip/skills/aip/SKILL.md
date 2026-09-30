---
name: aip
description: Design and review APIs against Google's API Improvement Proposals (AIPs, google.aip.dev), with every approved general AIP bundled and an api-linter wrapper. Use it whenever someone designs, writes or reviews a .proto file, gRPC service, protobuf message or resource-oriented REST API, including resource names and hierarchy, field naming, standard methods (Get/List/Create/Update/Delete), custom methods, pagination, filtering, field masks, long-running operations, error responses, field_behavior annotations, versioning or backwards compatibility. Also use it when an AIP is mentioned by number ("AIP-158"), when someone asks whether an API follows Google's API design guidelines, or when api-linter findings need fixing, even if the word "AIP" never comes up.
license: Apache-2.0 (skill and scripts, see LICENSE); bundled AIP text (c) Google LLC under CC BY 4.0, see NOTICE
compatibility: Linting needs Python 3, git and api-linter (go install github.com/googleapis/api-linter/v2/cmd/api-linter@latest). Everything else works without them.
---

# Google AIPs for API design and review

AIPs are Google's API design standards: one short document per topic, each
with numbered rules written as **must**, **should** and **may**. The approved
general AIPs are bundled in `references/aips/`, so answers come from the text
instead of memory. That matters because the AIPs change: for example,
`IDENTIFIER` field behavior on `name` and the guidance on the proto3
`optional` keyword (AIP-149) are both recent, and older blog posts and
training data contradict them.

## How to find the right AIP

1. Start from the index at the end of this file. It lists every bundled AIP
   by category.
2. Open the file `references/aips/NNNN-<slug>.md`, where NNNN is the
   zero-padded number (Glob `references/aips/0158-*` if unsure of the slug).
   Long AIPs start with a contents list; the **Guidance** section holds the
   rules and **Rationale** explains them.
3. `references/index.md` has a one-line summary per AIP for when the title
   alone doesn't tell you which one applies. Grep across `references/aips/`
   for a field or annotation name (`update_mask`, `operation_info`,
   `ErrorInfo`).
4. `references/examples/library/v1/book.proto` is a small, lint-clean API
   (a resource, the five standard methods, a custom state-changing method,
   pagination, filtering, an update mask, etags) to copy patterns from.

Read the relevant AIPs before answering, even when you think you know the
rule, and cite them as "AIP-NNN" so the reader can check. Keep **must** and
**should** apart: a **must** is a defect, a **should** is a strong default
that can be broken with a documented reason, and a **may** is optional. Take
the strength from the sentence in the AIP, not from memory and not from the
wording of an api-linter message (those sometimes say "should" for a
**must**); the reader will act on the label. When the AIP only recommends
something without a normative keyword, say "recommended" instead of inventing
a strength.

## Designing an API

Work outside-in, because each step constrains the next:

1. **Resources and hierarchy** (AIP-121, 122, 123, 124). Name the nouns,
   their parents, and resource name patterns such as
   `publishers/{publisher}/books/{book}`. Collection IDs are plural camelCase.
2. **Resource messages** (AIP-122, 123, 148, 203). `name` as the identifier
   with a `google.api.resource` annotation; standard fields (`create_time`,
   `update_time`, `display_name`, `uid`, `etag`) where they fit.
3. **Standard methods first** (AIP-130 to 135): Get, List, Create, Update,
   Delete with their exact request and response shapes and HTTP mappings.
   Reach for a custom method (AIP-136) only when a standard one cannot express
   the operation.
4. **Fields** (AIP-140 to 149, 203, 216): names, types, units, time, enums,
   and a `field_behavior` on every field of every message used in a request,
   the resource message included (the `etag` field is the exception).
5. **Cross-cutting patterns** as needed: pagination (158), filtering (160),
   ordering (132), field masks (161), long-running operations (151), request
   IDs for idempotency (155), etags (154), validate-only (163), soft delete
   (164), errors (193).
6. **Package and files** (AIP-185, 191): a versioned package such as
   `library.v1`, file layout, language package options.
7. **Lint** the result (see Linting) and fix or justify every finding.

Show the proto, not only prose. Put a comment on every element (AIP-192);
generated docs and client libraries depend on them. Any complete proto file you
hand over should compile and lint clean, imports included, because it will be
copied as-is.

## Reviewing an API

1. Run the linter on the files if it is available. It is fast and precise on
   mechanical issues, which leaves your attention for design.
2. Then review what a linter cannot judge: whether the resources model the
   domain, whether a custom method should have been a standard one, whether
   names are consistent across the API, whether a change breaks existing
   clients (AIP-180), and whether errors, idempotency and long-running work
   are handled. Think about the actual clients too: if the user named the
   languages or transports, check what the design means for them (int64
   is a string in proto JSON, and TypeScript generators differ: protobuf-es
   uses `bigint`, others `number` or `string`; large responses hit gRPC's
   default 4 MB message limit; REST clients see lowerCamelCase field names
   through transcoding).
3. Report findings in this shape, most important first:

```markdown
### <short title>  (AIP-NNN, must|should)
Where: file.proto:LINE, `Message.field` or `Rpc`
Problem: what is wrong and why it matters to API users.
Fix:
    <proto snippet or diff>
```

Group repeats (missing comments on twelve fields) into one finding. End with a
short list of what is already right, so the author knows what to keep.

For an API that isn't Google's, say which findings are Google-specific
conventions the team can reasonably skip (see Linting) instead of presenting
them as defects.

## Changing an API that has shipped

Before renaming, retyping, renumbering, removing or changing the behavior of
anything already released, read AIP-180. Most such changes break existing
clients at the wire level, in generated code, or in behavior. Additive changes
(new fields, methods, enum values) are usually safe. A breaking change belongs
in a new major version (AIP-185).

## Quick reference

The rules people most often get wrong, with the strength the AIP gives them.
Each row is a pointer, not a substitute: open the AIP when the details matter,
and read the exceptions it lists before calling something a defect.

| Instead of | Use | Strength | AIP |
|---|---|---|---|
| `created_at`, `updated_at`, `creation_date` | `create_time`, `update_time` as `google.protobuf.Timestamp` | must (148 standard fields); `_time` suffix in general: should | 148, 142 |
| `int32 timeout_seconds` for a span of time | `google.protobuf.Duration timeout` | should | 142 |
| `id` or `book_id` as the resource's identifier | `string name` with the full resource name, `field_behavior = IDENTIFIER` | must | 122, 203 |
| A List method without pagination "for now" | Pagination from the start; adding it later is breaking | must | 158 |
| `limit` / `offset` on list requests | `page_size` and `page_token` in the request, `next_page_token` in the response | should | 158 |
| `is_active`, `is_public` | `active`, `public` (booleans omit the `is` prefix, except to avoid a reserved word) | should | 140 |
| A singular name on a repeated field | The plural (`repeated string tags`) | must | 144 |
| An enum without a zero "unspecified" value | First value `<ENUM_NAME>_UNSPECIFIED = 0`, unless a real zero value such as `UNKNOWN` is clearer | should | 126 |
| `size`, `distance` holding a number with a unit | The unit as suffix: `size_bytes`, `distance_meters` | must | 141 |
| `float price` or `string currency` | `google.type.Money` for amounts; a field named `currency_code` (ISO 4217) for a bare currency | Money: recommended; `currency_code`: must | 143, 213 |
| Update taking the whole resource with no mask | The resource plus `google.protobuf.FieldMask update_mask`; HTTP `PATCH` | mask type and name: must; `PATCH`: should | 134, 161 |
| `CreateBookResponse` and similar wrappers | Get, Create and Update return the resource itself | must | 131, 133, 134 |
| Delete returning the deleted resource | `google.protobuf.Empty`; the resource only for soft delete | should | 135, 164 |
| A client-chosen ID mixed into the resource | `string book_id` on the Create request | must (management plane), should (data plane) | 133 |
| Unannotated fields in request messages | `(google.api.field_behavior)` on every field of every message used in a request, including the resource in Create and Update, with at least `REQUIRED`, `OPTIONAL` or `OUTPUT_ONLY`; the resource's `etag` gets none | must (etag: should not) | 203 |
| A `status` string that clients set | A nested `enum State`, field `state`, output only, changed through custom methods | should | 216 |
| Custom error payloads or bare status codes | `google.rpc.Status` with canonical codes and an `ErrorInfo` in `details` | must | 193 |
| An RPC that may take minutes returning its result | `google.longrunning.Operation` with an `operation_info` annotation, plus the `Operations` service | should use an LRO; once used, the annotation and service: must | 151 |
| No version, or `v1.2`, in the package | The major version at the end of the package: `library.v1`, `library.v1beta` | must | 185 |
| A custom method for what a standard method covers | The standard method; custom methods (`:verb`) are the exception | should | 136 |

## Linting

`scripts/lint.py` wraps [api-linter](https://linter.aip.dev), Google's
implementation of the AIP rules. In Claude Code the script is at
`${CLAUDE_SKILL_DIR}/scripts/lint.py` (use `python3` on macOS and Linux,
`python` on Windows):

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/lint.py" path/to/protos/ [more files or dirs]
python3 "${CLAUDE_SKILL_DIR}/scripts/lint.py" api/ -I third_party/protos --disable-rule core::0191::java-package
```

Point it at the files where they are. It works out each file's import root
from its `package` line (or the nearest `buf.yaml`), so a single file you just
wrote can be linted in place. Files that import each other by package path,
such as `import "library/v1/common.proto"`, need that directory layout or a
`-I` to the root that has it. The script fetches the googleapis common protos
(`google/api`, `google/rpc`, `google/type`, `google/longrunning`) into a cache
when an import needs them, picks up an `api-linter.yaml` from the current
directory, the import roots or their parents, and prints findings grouped by
AIP with paths relative to the current directory and the bundled AIP to read.
Exit code 0 means clean, 1 means findings, 2 means a setup or compile problem;
the message says what to install or which import is missing.

If api-linter is not installed, tell the user the install command the script
prints and carry on with a manual review. Don't install tools without asking.

A clean lint is not a good API. The linter checks shapes and names; it cannot
tell whether the resource model fits the domain.

The language package options in AIP-191 (`core::0191::java-package`,
`java-multiple-files`, `java-outer-classname`, and the C#, PHP and Ruby
equivalents) matter for Google's multi-language client libraries. Teams that
only generate Go or TypeScript often disable them. Disable a rule with
`--disable-rule`, with an `api-linter.yaml`:

```yaml
- included_paths: ["**/*.proto"]
  disabled_rules: ["core::0191::java-package"]
```

or with a comment, which keeps the reason next to the code. Put it directly
above the element the rule is about: a message, field or RPC for most rules,
and the `syntax` or `package` line for file-level rules such as the AIP-191
options:

```proto
// (-- api-linter: core::0191::java-package=disabled
//     aip.dev/not-precedent: We do not generate Java clients. --)
package library.v1;
```

Path patterns in an `api-linter.yaml` (`included_paths`, `excluded_paths`) are
matched against paths relative to each file's import root, such as
`library/v1/book.proto`, not relative to the config file.

## REST and OpenAPI

The AIPs are written against protobuf but describe HTTP APIs too. AIP-127 maps
each RPC to an HTTP verb and URI, and the standard methods give the REST shape:
`GET /v1/{name=publishers/*/books/*}`, `PATCH` with an update mask,
`POST /v1/{name=publishers/*/books/*}:archive` for a custom method. For an
OpenAPI or hand-written REST API, apply the same resource model, naming,
pagination and error rules, and translate proto field names to lowerCamelCase
JSON. api-linter only reads protos.

## AIP index

Process and meta AIPs (1 to 9, 100, 200, 205) are bundled as well; they cover
how AIPs are written and reviewed rather than how to design an API.

<!-- BEGIN GENERATED INDEX (tools/sync_aips.py) -->

- **API Concepts**: 111 Planes
- **Resource Design**: 121 Resource-oriented design, 122 Resource names, 123 Resource types, 124 Resource association, 126 Enumerations, 128 Declarative-friendly interfaces, 129 Server-Modified Values and Defaults, 156 Singleton resources, 236 Policy preview
- **Operations**: 130 Methods, 131 Standard methods: Get, 132 Standard methods: List, 133 Standard methods: Create, 134 Standard methods: Update, 135 Standard methods: Delete, 136 Custom methods, 151 Long-running operations, 231 Batch methods: Get, 233 Batch methods: Create, 234 Batch methods: Update, 235 Batch methods: Delete
- **Fields**: 140 Field names, 202 Fields, 203 Field behavior documentation, 141 Quantities, 142 Time and duration, 143 Standardized codes, 144 Repeated fields, 145 Ranges, 146 Generic fields, 147 Sensitive fields, 148 Standard fields, 149 Unset field values, 216 States
- **Design Patterns**: 152 Jobs, 153 Import and export, 154 Resource freshness validation, 155 Request identification, 157 Partial responses, 158 Pagination, 159 Reading across collections, 160 Filtering, 161 Field masks, 163 Change validation, 164 Soft delete, 165 Criteria-based delete, 210 Unicode, 211 Authorization checks, 214 Resource expiration, 217 Unreachable resources
- **Compatibility and Versioning**: 180 Backwards compatibility, 181 Stability levels, 184 API version identifiers, 185 API Versioning
- **Polish**: 190 Naming conventions, 191 File and directory structure, 192 Documentation, 193 Errors, 194 Automatic retry configuration
- **Protocol buffers**: 127 HTTP and gRPC Transcoding, 213 Common components, 215 API-specific protos

<!-- END GENERATED INDEX -->
