"""
Chunk Transcript Module

This module is responsible for dividing the cleaned transcript into smaller,
manageable chunks for further processing or analysis.
"""

from typing import Any


class ChunkTranscript:
    def __init__(self, chunk_size: int = 10, overlap: int = 15):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def invoke(self, segments: dict[str, Any]) -> dict[str, Any]:
        """
        Chunk cleaned transcript segments into smaller pieces.

        Handles:
        - Grouping transcript into 60-120 second time-aware chunks
        - Creating 10-20 second overlap between adjacent chunks
        - Preserving timing information for each chunk

        Input / Output:
            [{"text": str, "start": float, "end": float, "timecode": str}]
        """

        transcript = self._extract_transcript_segments(segments)
        segments["transcript_chunks"] = self.chunk_transcript(transcript, self.chunk_size, self.overlap,segments['source_id'])
        return segments

    def _extract_transcript_segments(
        self, payload: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Normalize transcript payloads into a list of transcript segment dicts."""

        transcript = payload.get("transcript", [])

        if isinstance(transcript, dict):
            transcript = transcript.get("transcript", [])

        if not isinstance(transcript, list):
            return []

        return [item for item in transcript if isinstance(item, dict)]

    def _format_seconds(self, total_seconds: float) -> str:
        """Convert seconds to HH:MM:SS.mmm format."""

        milliseconds = int(round(total_seconds * 1000))
        seconds_part = (milliseconds // 1000) % 60
        minutes_part = (milliseconds // 60000) % 60
        hours_part = milliseconds // 3600000
        millis_part = milliseconds % 1000
        return f"{hours_part:02}:{minutes_part:02}:{seconds_part:02}.{millis_part:03}"

    def chunk_transcript(
        self,
        segments: list[dict[str, Any]],
        chunk_size: int = 20,
        overlap: int = 10,
        source_id: str = "default",
    ) -> list[dict[str, Any]]:
        """
        Group transcript segments into time-aware chunks.

        Rules:
        - Targets chunks around ``chunk_size`` seconds.
        - Keeps chunks between 60 and 120 seconds when possible.
        - Starts the next chunk about ``overlap`` seconds before the previous one ends.
        """

        if not segments:
            return []

        min_chunk_duration = 10.0
        max_chunk_duration = 20.0
        target_chunk_duration = min(max(float(chunk_size), min_chunk_duration), max_chunk_duration)
        overlap_duration = max(0.0, float(overlap))

        normalized_segments = sorted(
            [segment for segment in segments if isinstance(segment, dict)],
            key=lambda seg: (float(seg.get("start", 0.0)), float(seg.get("end", 0.0))),
        )

        if not normalized_segments:
            return []

        chunks: list[dict[str, Any]] = []
        start_idx = 0

        while start_idx < len(normalized_segments):
            chunk_segments: list[dict[str, Any]] = []
            chunk_start = float(normalized_segments[start_idx].get("start", 0.0))
            chunk_end = chunk_start
            end_idx = start_idx

            while end_idx < len(normalized_segments):
                segment = normalized_segments[end_idx]
                segment_end = float(segment.get("end", segment.get("start", 0.0)))
                candidate_duration = segment_end - chunk_start

                chunk_segments.append(segment)
                chunk_end = segment_end
                text = str(segment.get("text", "")).strip()
                reached_min = candidate_duration >= min_chunk_duration
                reached_target = candidate_duration >= target_chunk_duration
                would_exceed_max = False

                if end_idx + 1 < len(normalized_segments):
                    next_end = float(
                        normalized_segments[end_idx + 1].get(
                            "end",
                            normalized_segments[end_idx + 1].get("start", 0.0),
                        )
                    )
                    would_exceed_max = (next_end - chunk_start) > max_chunk_duration

                if reached_min and (
                    would_exceed_max
                    or (reached_target and text.endswith((".", "!", "?")))
                ):
                    break

                if candidate_duration >= max_chunk_duration:
                    break

                end_idx += 1

            chunk_text = " ".join(
                str(segment.get("text", "")).strip()
                for segment in chunk_segments
                if str(segment.get("text", "")).strip()
            )

            chunks.append({
                    "id": f'{source_id}_{str(len(chunks)+1)}',
                    "text": chunk_text,
                    'metadata' : {
                    "start": chunk_start,
                    "end": chunk_end,
                    "duration": round(chunk_end - chunk_start, 3),
                    "timecode": (
                        f"{self._format_seconds(chunk_start)} --> "
                        f"{self._format_seconds(chunk_end)}"
                    ),
                    "segment_count": len(chunk_segments),
                 }
                    }
            )

            if end_idx >= len(normalized_segments) - 1:
                break

            next_start_time = max(chunk_start + 0.001, chunk_end - overlap_duration)
            next_start_idx = end_idx + 1

            for idx in range(start_idx + 1, len(normalized_segments)):
                segment = normalized_segments[idx]
                segment_start = float(segment.get("start", 0.0))
                segment_end = float(segment.get("end", segment_start))

                if segment_end > next_start_time or segment_start >= next_start_time:
                    next_start_idx = idx
                    break

            if next_start_idx <= start_idx:
                next_start_idx = start_idx + 1

            start_idx = next_start_idx

        return chunks
