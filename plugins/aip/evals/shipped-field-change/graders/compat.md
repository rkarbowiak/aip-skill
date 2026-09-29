---
type: llm
---
The answer must explain that renaming `customer` to `buyer` is a breaking change for JSON/REST clients and generated code even though the binary wire format is unaffected, and that changing int32 to int64 in place is treated as a breaking change by AIP-180 (generated code types change; JSON encodes int64 as a string) even though protobuf's binary wire format can read it. It should recommend an additive path (new field, deprecate old) or a new major version, and reference AIP-180. Pass if all of this is present and correct.
