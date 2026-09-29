---
type: llm
---
The proto should follow Google AIPs: Episode is a resource with `string name` and a google.api.resource pattern like shows/{show}/episodes/{episode}; standard methods Get/List/Create/Update/Delete with correct request shapes (parent on List/Create, update_mask on Update, Delete returning google.protobuf.Empty or the resource only if soft-deleting); newest-first listing via an `order_by` field or documented default ordering; transcription as a custom method (e.g. `:transcribe`) returning a long-running operation; google.api.field_behavior annotations on request fields; timestamps named *_time. Pass if the design meets nearly all of these with no significant AIP violations.
