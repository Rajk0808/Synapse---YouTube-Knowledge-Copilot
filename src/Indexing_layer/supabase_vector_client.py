import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
from supabase import Client, create_client


class SupabaseVectorClient:
    """Supabase adapter that stores document/chunk metadata and vectors."""

    def __init__(self, supabase_url: str, supabase_key: str):
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.")

        self.client: Client = create_client(supabase_url, supabase_key)

    def _stable_uuid(self, seed: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))

    def _require_tenant_fields(self, document: dict[str, Any]) -> tuple[str, str]:
        workspace_id = str(document.get("workspace_id") or "").strip()
        owner_user_id = str(document.get("owner_user_id") or "").strip()

        if not workspace_id or not owner_user_id:
            raise ValueError(
                "Missing tenant fields. Provide workspace_id and owner_user_id in indexing payload."
            )

        return workspace_id, owner_user_id

    def _upsert_video(self, document: dict[str, Any]) -> str:
        workspace_id, owner_user_id = self._require_tenant_fields(document)
        source_url = str(document.get("source_url") or "")
        source_type = str(document.get("type") or "youtube_video")

        video_id = str(document.get("video_id") or self._stable_uuid(f"video::{document.get('document_id')}"))

        payload = {
            "id": video_id,
            "workspace_id": workspace_id,
            "owner_user_id": owner_user_id,
            "source_url": source_url,
            "source_type": source_type,
            "title": document.get("title"),
            "channel_name": document.get("channel"),
            "duration_seconds": document.get("duration_seconds"),
            "publish_date": document.get("published_at"),
            "transcript_status": "available",
            "visibility": "private",
        }

        self.client.table("videos").upsert(payload, on_conflict="id").execute()
        return video_id

    def _upsert_chunks(self, video_id: str, chunks: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        chunk_rows: list[dict[str, Any]] = []
        vector_rows: list[dict[str, Any]] = []

        for chunk in chunks:
            workspace_id = str(chunk.get("workspace_id") or "").strip()
            owner_user_id = str(chunk.get("owner_user_id") or "").strip()
            if not workspace_id or not owner_user_id:
                raise ValueError("Each chunk requires workspace_id and owner_user_id.")

            chunk_id = str(chunk.get("chunk_id"))
            chunk_key = f"{chunk.get('document_id')}::{chunk_id}"
            chunk_row_id = self._stable_uuid(f"chunk::{chunk_key}")
            vector_document_id = chunk_key

            chunk_rows.append(
                {
                    "id": chunk_row_id,
                    "workspace_id": workspace_id,
                    "owner_user_id": owner_user_id,
                    "video_id": video_id,
                    "chunk_index": int(chunk.get("chunk_index", 0)),
                    "chunk_text": chunk.get("text", ""),
                    "start_time_seconds": float(chunk.get("start_time_seconds", 0.0)),
                    "end_time_seconds": float(chunk.get("end_time_seconds", 0.0)),
                    "timecode": chunk.get("timecode", ""),
                    "topic": chunk.get("topic"),
                    "difficulty": chunk.get("difficulty"),
                    "speaker": chunk.get("speaker"),
                    "language": chunk.get("language", "en"),
                    "visibility": "private",
                    "vector_document_id": vector_document_id,
                }
            )

            embedding = chunk.get("embedding", [])
            if embedding:
                vector_rows.append(
                    {
                        "vector_document_id": vector_document_id,
                        "workspace_id": workspace_id,
                        "owner_user_id": owner_user_id,
                        "video_id": video_id,
                        "document_id": chunk.get("document_id"),
                        "chunk_id": chunk_id,
                        "chunk_index": int(chunk.get("chunk_index", 0)),
                        "embedding": embedding,
                        "chunk_text": chunk.get("text", ""),
                        "metadata": {
                            "timecode": chunk.get("timecode"),
                            "topic": chunk.get("topic"),
                            "difficulty": chunk.get("difficulty"),
                            "speaker": chunk.get("speaker"),
                            "language": chunk.get("language", "en"),
                            "source_video": chunk.get("source_video"),
                            "artifacts": chunk.get("artifacts", {}),
                        },
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                )

        if chunk_rows:
            self.client.table("transcript_chunks").upsert(
                chunk_rows,
                on_conflict="video_id,chunk_index",
            ).execute()

        if vector_rows:
            self.client.table("transcript_chunk_vectors").upsert(
                vector_rows,
                on_conflict="vector_document_id",
            ).execute()

        return chunk_rows, vector_rows

    def _upsert_keyword_index(self, document: dict[str, Any], keyword_index: dict[str, Any]) -> None:
        workspace_id, owner_user_id = self._require_tenant_fields(document)
        document_id = str(document.get("document_id"))

        self.client.table("keyword_indexes").upsert(
            {
                "document_id": document_id,
                "workspace_id": workspace_id,
                "owner_user_id": owner_user_id,
                "index_payload": keyword_index,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="document_id",
        ).execute()

    def upsert_document(
        self,
        document: dict[str, Any],
        chunks: list[dict[str, Any]],
        vectors: np.ndarray,
        vector_metadata: list[dict[str, Any]],
        keyword_index: dict[str, Any],
    ) -> dict[str, Any]:
        """Persist document, chunks, vectors, and keyword index into Supabase."""

        video_id = self._upsert_video(document)
        chunk_rows, vector_rows = self._upsert_chunks(video_id=video_id, chunks=chunks)
        self._upsert_keyword_index(document=document, keyword_index=keyword_index)

        return {
            "status": "ok",
            "video_id": video_id,
            "chunk_rows": len(chunk_rows),
            "vector_rows": len(vector_rows),
            "vector_dim": int(vectors.shape[1]) if vectors.ndim == 2 and vectors.size else 0,
            "vector_metadata_rows": len(vector_metadata),
        }
