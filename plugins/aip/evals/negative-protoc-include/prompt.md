---
description: Near miss - protoc build error, not API design
tags: [negative]
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---
running `protoc --go_out=. api/user.proto` gives "google/protobuf/timestamp.proto: File not found." on my mac (installed protoc from the github zip). how do i fix the include path?
