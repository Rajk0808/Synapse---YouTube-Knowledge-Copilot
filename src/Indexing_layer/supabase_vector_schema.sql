CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS transcript_chunk_vectors (
    vector_document_id TEXT PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    document_id TEXT NOT NULL,
    chunk_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    embedding VECTOR(768) NOT NULL,
    chunk_text TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transcript_chunk_vectors_workspace_id
ON transcript_chunk_vectors(workspace_id);

CREATE INDEX IF NOT EXISTS idx_transcript_chunk_vectors_owner_user_id
ON transcript_chunk_vectors(owner_user_id);

CREATE INDEX IF NOT EXISTS idx_transcript_chunk_vectors_video_id
ON transcript_chunk_vectors(video_id);

CREATE INDEX IF NOT EXISTS idx_transcript_chunk_vectors_embedding
ON transcript_chunk_vectors
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE TABLE IF NOT EXISTS keyword_indexes (
    document_id TEXT PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    index_payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_keyword_indexes_workspace_id
ON keyword_indexes(workspace_id);

CREATE INDEX IF NOT EXISTS idx_keyword_indexes_owner_user_id
ON keyword_indexes(owner_user_id);
