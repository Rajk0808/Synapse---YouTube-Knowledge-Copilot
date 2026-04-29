CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    preferred_language TEXT DEFAULT 'en',
    response_style TEXT DEFAULT 'concise',
    expertise_level TEXT DEFAULT 'beginner',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workspace_members (
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'member',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (workspace_id, user_id)
);

CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    created_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_url TEXT NOT NULL,
    source_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS videos (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ingestion_job_id UUID REFERENCES ingestion_jobs(id) ON DELETE SET NULL,
    external_video_id TEXT,
    source_url TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'youtube_video',
    title TEXT,
    channel_name TEXT,
    duration_seconds INTEGER,
    publish_date DATE,
    transcript_status TEXT NOT NULL DEFAULT 'available',
    transcript_storage_path TEXT,
    visibility TEXT NOT NULL DEFAULT 'private',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transcript_chunks (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    start_time_seconds DOUBLE PRECISION NOT NULL,
    end_time_seconds DOUBLE PRECISION NOT NULL,
    timecode TEXT NOT NULL,
    topic TEXT,
    difficulty TEXT,
    speaker TEXT,
    language TEXT DEFAULT 'en',
    visibility TEXT NOT NULL DEFAULT 'private',
    vector_document_id TEXT UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (video_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_videos_workspace_id ON videos(workspace_id);
CREATE INDEX IF NOT EXISTS idx_videos_owner_user_id ON videos(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_transcript_chunks_workspace_id ON transcript_chunks(workspace_id);
CREATE INDEX IF NOT EXISTS idx_transcript_chunks_video_id ON transcript_chunks(video_id);
CREATE INDEX IF NOT EXISTS idx_transcript_chunks_owner_user_id ON transcript_chunks(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_transcript_chunks_visibility ON transcript_chunks(visibility);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    cited_video_id UUID REFERENCES videos(id) ON DELETE SET NULL,
    cited_chunk_ids JSONB,
    grounding_score DOUBLE PRECISION,
    latency_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);

CREATE TABLE IF NOT EXISTS generated_artifacts (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL,
    title TEXT,
    content JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_generated_artifacts_workspace_id ON generated_artifacts(workspace_id);
CREATE INDEX IF NOT EXISTS idx_generated_artifacts_video_id ON generated_artifacts(video_id);