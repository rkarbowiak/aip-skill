---
description: Changing a field of an API that is already in production
tags: [compatibility, trigger]
max_turns: 20
allowed_tools: [Read, Glob, Grep, Skill]
---
our orders.v1 gRPC API is live and used by partners. i want to change `int32 quantity = 4;` to `int64 quantity = 4;` and rename `customer` to `buyer` in the Order message while i'm at it. any gotchas?
