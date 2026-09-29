---
type: llm
---
The review must identify all of these problems and give the AIP-aligned fix:
1. limit/offset pagination should be page_size/page_token with next_page_token in the response.
2. `id` fields should be replaced by a `name` resource name (e.g. products/{product}), and `name` must not be used for a human-readable title (use display_name or title).
3. created_at should be create_time.
4. is_available should drop the "is" prefix; repeated `tag` should be plural `tags`.
5. CreateProductResponse should go away: Create returns the Product; errors use gRPC status instead of `ok`.
6. The package should carry a major version (e.g. shop.v1).
Pass only if at least five of the six are present and none of the advice contradicts them.
