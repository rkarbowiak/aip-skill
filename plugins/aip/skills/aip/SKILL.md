---
name: aip
description: Design and review APIs against Google's API Improvement Proposals (AIPs, google.aip.dev), with every approved AIP bundled and an api-linter wrapper. Use it whenever someone designs, writes or reviews a .proto file, gRPC service, protobuf message or resource-oriented REST API, including resource names and hierarchy, field naming, standard methods (Get/List/Create/Update/Delete), custom methods, pagination, filtering, field masks, long-running operations, error responses, field_behavior annotations, versioning or backwards compatibility. Also use it when an AIP is mentioned by number ("AIP-158"), when someone asks whether an API follows Google's API design guidelines, or when api-linter findings need fixing, even if the word "AIP" never comes up.
license: Apache-2.0 (skill and scripts); bundled AIP text is CC BY 4.0 by Google, see NOTICE
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
4. `references/examples/agenda/v1/talk.proto` is a small, lint-clean API
   (a resource, the five standard methods, pagination, an update mask) to
   copy patterns from.

Read the relevant AIPs before answering, even when you think you know the
rule, and cite them as "AIP-NNN" so the reader can check. Keep **must** and
**should** apart: a **must** is a defect, a **should** is a strong default
that can be broken with a documented reason, and a **may** is optional. Take
the strength from the sentence in the AIP, not from memory; it is easy to
remember a **must** as a **should** and the reader will act on the label.

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
   and a `field_behavior` on every request field.
5. **Cross-cutting patterns** as needed: pagination (158), filtering (160),
   ordering (132), field masks (161), long-running operations (151), request
   IDs for idempotency (155), etags (154), validate-only (163), soft delete
   (164), errors (193).
6. **Package and files** (AIP-185, 191): a versioned package such as
   `agenda.v1`, file layout, language package options.
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
   becomes a string in JSON and a `bigint` in TypeScript; large responses
   hit gRPC's default 4 MB message limit; REST clients see lowerCamelCase
   field names through transcoding).
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

The rules people most often get wrong. Each row is a pointer, not a
substitute: open the AIP when the details matter.

| Instead of | Use | AIP |
|---|---|---|
| `created_at`, `updated_at`, `creation_date` | `create_time`, `update_time` as `google.protobuf.Timestamp` (`_time` suffix) | 142, 148 |
| `int32 timeout_seconds` for a span of time | `google.protobuf.Duration timeout` | 142 |
| `id` or `talk_id` as the resource's identifier | `string name` with the full resource name, `field_behavior = IDENTIFIER` | 122, 203 |
| `limit` / `offset` on list requests | `page_size` and `page_token` in the request, `next_page_token` in the response | 158 |
| A List method without pagination "for now" | Pagination from the start; adding it later is a breaking change | 158 |
| `is_active`, `is_public` | `active`, `public` (booleans omit the `is` prefix) | 140 |
| A singular name on a repeated field | The plural (`repeated string tags`) | 140, 144 |
| An enum without a zero "unspecified" value | First value `<ENUM_NAME>_UNSPECIFIED = 0` | 126 |
| `size`, `distance` holding a number with a unit | The unit as suffix: `size_bytes`, `distance_meters` | 141 |
| `float price` or `string currency` | `google.type.Money` for amounts; a `currency_code` field (ISO 4217) for a bare currency | 143, 213 |
| Update taking the whole resource with no mask | The resource plus `google.protobuf.FieldMask update_mask`, HTTP `PATCH` | 134, 161 |
| `CreateTalkResponse` and similar wrappers | Get, Create and Update return the resource itself | 131, 133, 134 |
| Delete returning the deleted resource | `google.protobuf.Empty`; the resource only for soft delete | 135, 164 |
| A client-chosen ID mixed into the resource | `string talk_id` on the Create request | 133 |
| Request fields without annotations | `(google.api.field_behavior)` on every request field, at least `REQUIRED`, `OPTIONAL` or `OUTPUT_ONLY` | 203 |
| A `status` string that clients set | A nested `enum State`, field `state`, `OUTPUT_ONLY`, changed through custom methods | 216 |
| Custom error payloads or bare status codes | `google.rpc.Status` with canonical codes and an `ErrorInfo` in `details` | 193 |
| An RPC that may take minutes returning its result | `google.longrunning.Operation` with an `operation_info` annotation | 151 |
| No version, or `v1.2`, in the package | The major version at the end of the package: `agenda.v1`, `agenda.v1beta` | 185 |
| A custom method for what a standard method covers | The standard method; custom methods (`:verb`) are the exception | 136 |

## Linting

`scripts/lint.py` wraps [api-linter](https://linter.aip.dev), Google's
implementation of the AIP rules. In Claude Code the script is at
`${CLAUDE_SKILL_DIR}/scripts/lint.py`:

```bash
python "${CLAUDE_SKILL_DIR}/scripts/lint.py" path/to/protos/ [more files or dirs]
python "${CLAUDE_SKILL_DIR}/scripts/lint.py" api/ -I third_party/protos --disable-rule core::0191::java-package
```

Point it at files where they are; there is no need to copy them into a
directory tree matching the package. It works out the import root from each
file's `package` line when the layout matches, fetches the
googleapis common protos (`google/api`, `google/rpc`, `google/type`,
`google/longrunning`) into a cache on first use, picks up the project's
`api-linter.yaml` if there is one, and prints findings grouped by AIP with the
path of the bundled AIP to read. Exit code 0 means clean, 1 means findings,
2 means a setup or compile problem; the message says what to install or which
import is missing.

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

or with a comment on the element, which keeps the reason next to the code:

```proto
// (-- api-linter: core::0191::java-package=disabled
//     aip.dev/not-precedent: We do not generate Java clients. --)
```

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
