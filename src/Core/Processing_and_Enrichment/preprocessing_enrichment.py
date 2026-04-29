from datetime import datetime

from src.Core.Processing_and_Enrichment.artifacts import Artifacts
from src.Core.Processing_and_Enrichment.cleaning import Cleaning
from src.Core.Processing_and_Enrichment.chunk_transcript import ChunkTranscript
from src.Core.Processing_and_Enrichment.embeddings import Embeddings
from src.Core.Processing_and_Enrichment.tagging import Tagging

class preprocessing_enrichment:
    def __init__(self):
        self.cleaning = Cleaning()
        self.chunk_transcript = ChunkTranscript()
        self.embeddings = Embeddings()
        self.artifacts = Artifacts()
        self.tagging = Tagging()

    def _normalize_date(self, value: str | None) -> str | None:
        """Normalize dates to YYYY-MM-DD when possible."""

        if not value:
            return None

        if len(value) == 8 and value.isdigit():
            try:
                return datetime.strptime(value, "%Y%m%d").strftime("%Y-%m-%d")
            except ValueError:
                return value

        return value

    def _build_document(self, data: dict) -> dict:
        """Normalize document-level metadata for downstream consumers."""

        return {
            "type": data.get("type", "video"),
            "source_url": data.get("source_url"),
            "title": data.get("title"),
            "channel": data.get("channel") or data.get("uploader"),
            "published_at": self._normalize_date(data.get("published_at") or data.get("upload_date")),
            "duration_seconds": data.get("duration_seconds") or data.get("duration"),
            "view_count": data.get("view_count"),
            "like_count": data.get("like_count"),
            "comment_count": data.get("comment_count"),
            "workspace_id": data.get("workspace_id"),
            "owner_user_id": data.get("owner_user_id"),
        }

    def _build_transcript(self, data: dict) -> dict:
        """Collect transcript-level fields into one stable shape."""

        cleaned_segments = data.get("transcript", [])
        transcript_text = data.get("transcript_text", "")

        if not transcript_text:
            transcript_text = " ".join(
                str(segment.get("text", "")).strip()
                for segment in cleaned_segments
                if str(segment.get("text", "")).strip()
            )

        return {
            "text": transcript_text,
            "segments": cleaned_segments,
            "chunk_count": len(data.get("transcript_chunks", [])),
            "error": data.get("transcript_error"),
        }

    def invoke(self, data: dict) -> dict:
        """Preprocess and enrich YouTube chat data by cleaning, chunking, generating embeddings, and creating artifacts."""
        
        cleaned_data = self.cleaning.invoke(data)
        chunked_data = self.chunk_transcript.invoke(cleaned_data)
        enriched_data = self.embeddings.invoke(chunked_data)
        tagged_data =  self.tagging.invoke(enriched_data)
        result = self.artifacts.invoke(tagged_data)

        transcript_text = " ".join(
            str(segment.get("text", "")).strip()
            for segment in result.get("transcript", [])
            if str(segment.get("text", "")).strip()
        )

        if not transcript_text:
            transcript_text = " ".join(
            str(chunk.get("text", "")).strip()
            for chunk in result.get("transcript_chunks", [])
            if str(chunk.get("text", "")).strip()
            )
        result["transcript_text"] = transcript_text

        return {
            "document": self._build_document(result),
            "transcript": self._build_transcript(result),
            "chunks": result.get("transcript_chunks", []),
            "artifacts": result.get("artifacts", {}),
        }
