# Multi-User Data Model for YouTube Knowledge Copilot

## Goal

Support many users without creating a separate vector database per user.

Recommended approach:

- Use one shared vector collection/index for transcript chunks
- Use metadata filters for tenant and ownership boundaries
- Store users, sessions, permissions, and artifacts in PostgreSQL

This gives you:

- simpler infrastructure
- easier scaling
- lower cost
- cleaner retrieval logic

Create separate vector databases only for strict enterprise isolation or compliance-heavy use cases.

## High-Level Design

### PostgreSQL stores

- users
- workspaces
- workspace_members
- ingestion jobs
- videos
- transcript_chunks
- chat_sessions
- chat_messages
- generated_artifacts

### Vector DB stores

- chunk embeddings only
- chunk text
- retrieval metadata for filtering

## Multi-Tenant Strategy

Each chunk in the vector DB should carry metadata like:

- workspace_id
- owner_user_id
- video_id
- source_type
- topic
- start_time
- end_time
- visibility

At query time, retrieve only from chunks where:

- `workspace_id` matches the current workspace
- `visibility` allows access
- optional filters like `video_id`, `topic`, or time range also match

## Recommended Vector Metadata

```json
{
  "chunk_id": "chunk_001",
  "workspace_id": "ws_123",
  "owner_user_id": "user_456",
  "video_id": "yt_dhSJKmbHaEY",
  "video_title": "Sample Video",
  "channel_name": "Sample Channel",
  "source_type": "youtube_video",
  "visibility": "private",
  "topic": "transformers",
  "difficulty": "beginner",
  "start_time": 120.5,
  "end_time": 185.2,
  "timecode": "00:02:00.500 --> 00:03:05.200",
  "language": "en"
}
```

## Retrieval Flow

1. User sends a question in a workspace
2. App loads user identity and workspace membership from PostgreSQL
3. Retrieval service builds vector DB filters from access scope
4. Vector search runs only on allowed chunks
5. Optional BM25 search runs on the same allowed chunk set
6. Hybrid merge and reranking produce final evidence
7. LLM answers with timestamp citations
8. Session, answer, evidence, and latency are logged

## Access Rules

Use these rules for a strong MVP:

- `private`: only owner and workspace members can access
- `workspace`: any member in the workspace can access
- `public`: anyone in the app can access

For a 2-week build, `workspace` and `private` are enough.

## What To Keep Out of the Vector DB

Do not store these as your source of truth in the vector store:

- passwords
- auth data
- session state
- billing data
- user settings
- full artifact history

Those belong in PostgreSQL.

## Practical Recommendation for Your Project

For now, use:

- one vector collection called `transcript_chunks`
- one PostgreSQL database for app data
- `workspace_id` as the main tenant key
- `owner_user_id` for ownership
- `video_id` for source filtering

This is the right default for a portfolio-ready RAG system.
