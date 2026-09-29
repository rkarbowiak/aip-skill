---
description: Design a small API that needs pagination and a long-running method
tags: [design, trigger]
max_turns: 25
allowed_tools: [Read, Glob, Grep, Skill]
---
We're building a gRPC API for a podcast hosting platform: shows and episodes under shows. Need CRUD for episodes, listing episodes of a show newest first, and a "transcribe episode" action that runs speech-to-text and takes up to 20 minutes. Can you sketch the proto for the episode part (package podcasts.v1)? Just reply with the proto and a few notes.
