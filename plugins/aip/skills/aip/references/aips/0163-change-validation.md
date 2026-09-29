# AIP-163: Change validation

> Source: <https://google.aip.dev/163> (state: approved, category: design-patterns).
> Copied from aip-dev/google.aip.dev@23e176e7333e under CC BY 4.0 (text) and
> Apache 2.0 (code samples). Changes: front matter removed, title prefixed,
> contents list added, links rewritten to local files.

Occasionally, a user wants to validate an intended change to see what the
result will be before actually making the change. For example, a request to
provision new servers in a fleet will have an impact on the overall fleet size
and cost, and could potentially have unexpected downstream effects.

## Guidance

APIs **may** provide an option to validate, but not actually execute, a
request, and provide the same response (status code, headers, and response
body) that it would have provided if the request was actually executed.

To provide this option, the method **should** include a `bool validate_only`
field in the request message:

```proto
message ReviewBookRequest {
  string name = 1 [(google.api.resource_reference) = {
    type: "library.googleapis.com/Book"
  }];
  int32 rating = 2;
  string comment = 3;

  // If set, validate the request and preview the review, but do not actually
  // post it.
  bool validate_only = 4;
}
```

The API **must** perform permission checks and any other validation that would
be performed on a "live" request; a request using `validate_only` **must** fail
if it determines that the actual request would fail.

**Note:** It may occasionally be infeasible to provide the full output. For
example, if creating a resource would create an auto-generated ID, it does not
make sense to do this on validation. APIs **should** omit such fields on
validation requests in this situation.

### Declarative-friendly resources

A resource that is declarative-friendly (AIP-128) **must** include a
`validate_only` field on methods that mutate the resource.

## Changelog

- **2020-10-06:** Added declarative-friendly resource requirement.
