---
description: Review of a small proto with typical AIP violations
tags: [review, trigger]
max_turns: 25
allowed_tools: [Read, Glob, Grep, Skill]
---
Quick review before we ship this as our public API please. What would you change?

```proto
syntax = "proto3";
package shop;

import "google/protobuf/timestamp.proto";

service ProductService {
  rpc GetProduct(GetProductRequest) returns (Product);
  rpc ListProducts(ListProductsRequest) returns (ListProductsResponse);
  rpc CreateProduct(CreateProductRequest) returns (CreateProductResponse);
}

message Product {
  string id = 1;
  string name = 2;
  bool is_available = 3;
  google.protobuf.Timestamp created_at = 4;
  repeated string tag = 5;
}

message GetProductRequest { string id = 1; }
message ListProductsRequest { int32 limit = 1; int32 offset = 2; }
message ListProductsResponse { repeated Product products = 1; }
message CreateProductRequest { Product product = 1; }
message CreateProductResponse { Product product = 1; bool ok = 2; }
```
