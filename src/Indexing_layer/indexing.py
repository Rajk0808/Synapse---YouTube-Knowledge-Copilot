import hashlib
import json
import math
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Protocol

import numpy as np


class VectorDBClient(Protocol):
    """Contract for pushing indexed content to a remote vector database."""

    def upsert_document(
        self,
        document: dict[str, Any],
        chunks: list[dict[str, Any]],
        vectors: np.ndarray,
        vector_metadata: list[dict[str, Any]],
        keyword_index: dict[str, Any],
    ) -> dict[str, Any] | None:
        ...
class IndexingLayer:
    """Indexing layer with local and/or vector DB persistence."""

    TOKEN_PATTERN = re.compile(r"\b\w+\b", re.IGNORECASE)

    def __init__(
        self,
        index_root: str = "data/index",
        storage_mode: Literal["local", "vectordb", "both"] = "local",
        vector_db_client: VectorDBClient | None = None,
    ):
        if storage_mode not in {"local", "vectordb", "both"}:
            raise ValueError("storage_mode must be one of: local, vectordb, both")

        self.storage_mode = storage_mode
        self.vector_db_client = vector_db_client
        self.index_root = Path(index_root)
        self.documents_dir = self.index_root / "documents"
        self.vectors_dir = self.index_root / "vectors"
        self.keyword_dir = self.index_root / "keyword"
        self.manifest_path = self.index_root / "manifest.json"

        if self._is_local_enabled:
            self.documents_dir.mkdir(parents=True, exist_ok=True)
            self.vectors_dir.mkdir(parents=True, exist_ok=True)
            self.keyword_dir.mkdir(parents=True, exist_ok=True)

    @property
    def _is_local_enabled(self) -> bool:
        return self.storage_mode in {"local", "both"}

    @property
    def _is_vectordb_enabled(self) -> bool:
        return self.storage_mode in {"vectordb", "both"}

    def _stable_document_id(self, payload: dict[str, Any]) -> str:
        source_url = str(payload.get("document", {}).get("source_url") or "")
        if not source_url:
            source_url = str(payload.get("document", {}).get("title") or "untitled")
        return hashlib.sha256(source_url.encode("utf-8")).hexdigest()[:16]

    def _stable_uuid(self, seed: str) -> str:
        """Generate deterministic UUIDs for idempotent upserts."""

        return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))

    def _ensure_float_embedding(self, embedding: Any) -> list[float]:
        if not isinstance(embedding, list):
            return []

        vector: list[float] = []
        for value in embedding:
            try:
                vector.append(float(value))
            except (TypeError, ValueError):
                return []

        return vector

    def _tokenize(self, text: str) -> list[str]:
        return [token.lower() for token in self.TOKEN_PATTERN.findall(text or "")]

    def _build_chunk_records(self, payload: dict[str, Any], document_id: str) -> list[dict[str, Any]]:
        chunks = payload.get("chunks", [])
        document = payload.get("document", {})

        workspace_id = document.get("workspace_id")
        owner_user_id = document.get("owner_user_id")
        chunk_records: list[dict[str, Any]] = []

        for index, chunk in enumerate(chunks):
            if not isinstance(chunk, dict):
                continue

            raw_tags = chunk.get("tags")
            tags = raw_tags if isinstance(raw_tags, dict) else {}

            text = str(chunk.get("text", ""))
            chunk_records.append(
                {
                    "document_id": document_id,
                    "workspace_id": workspace_id,
                    "owner_user_id": owner_user_id,
                    "chunk_id": str(chunk.get("chunk_id") or index + 1),
                    "chunk_index": index,
                    "text": text,
                    "tokens": self._tokenize(text),
                    "start_time_seconds": float(chunk.get("start", 0.0)),
                    "end_time_seconds": float(chunk.get("end", 0.0)),
                    "timecode": str(chunk.get("timecode", "")),
                    "topic": tags.get("topic"),
                    "difficulty": tags.get("difficulty"),
                    "speaker": tags.get("speaker"),
                    "language": tags.get("language") or "en",
                    "source_video": payload.get("document", {}).get("source_url"),
                    "artifacts": chunk.get("artifacts", {}),
                    "embedding": self._ensure_float_embedding(chunk.get("embedding", [])),
                }
            )

        return chunk_records

    def _build_document_record(self, payload: dict[str, Any], document_id: str) -> dict[str, Any]:
        document = payload.get("document", {})

        return {
            "document_id": document_id,
            "video_id": self._stable_uuid(f"video::{document_id}"),
            "workspace_id": document.get("workspace_id"),
            "owner_user_id": document.get("owner_user_id"),
            "type": document.get("type", "video"),
            "source_url": document.get("source_url"),
            "title": document.get("title"),
            "channel": document.get("channel"),
            "published_at": document.get("published_at"),
            "duration_seconds": document.get("duration_seconds"),
            "indexed_at": datetime.now(timezone.utc).isoformat(),
            "transcript": payload.get("transcript", {}),
            "artifacts": payload.get("artifacts", {}),
        }

    def _build_vector_index(self, chunk_records: list[dict[str, Any]]) -> tuple[np.ndarray, list[dict[str, Any]]]:
        vectors: list[list[float]] = []
        metadata: list[dict[str, Any]] = []

        expected_dim: int | None = None
        for record in chunk_records:
            embedding = record.get("embedding", [])
            if not embedding:
                continue

            if expected_dim is None:
                expected_dim = len(embedding)

            if len(embedding) != expected_dim:
                continue

            vectors.append(embedding)
            metadata.append(
                {
                    "document_id": record["document_id"],
                    "workspace_id": record.get("workspace_id"),
                    "owner_user_id": record.get("owner_user_id"),
                    "chunk_id": record["chunk_id"],
                    "chunk_index": record["chunk_index"],
                    "text": record["text"],
                    "timecode": record["timecode"],
                    "start_time_seconds": record["start_time_seconds"],
                    "end_time_seconds": record["end_time_seconds"],
                    "topic": record.get("topic"),
                    "difficulty": record.get("difficulty"),
                    "speaker": record.get("speaker"),
                    "language": record.get("language"),
                    "source_video": record.get("source_video"),
                }
            )

        if not vectors:
            return np.empty((0, 0), dtype=np.float32), []

        matrix = np.asarray(vectors, dtype=np.float32)
        return matrix, metadata

    def _build_keyword_index(self, chunk_records: list[dict[str, Any]]) -> dict[str, Any]:
        """Build BM25-compatible statistics for keyword retrieval."""

        doc_freq: dict[str, int] = {}
        doc_lens: list[int] = []
        term_freqs: list[dict[str, int]] = []
        ids: list[str] = []

        for record in chunk_records:
            tokens = record.get("tokens", [])
            token_counts = Counter(tokens)

            doc_lens.append(len(tokens))
            term_freqs.append(dict(token_counts))
            ids.append(f"{record['document_id']}::{record['chunk_id']}")

            for token in token_counts.keys():
                doc_freq[token] = doc_freq.get(token, 0) + 1

        avg_doc_len = float(sum(doc_lens) / len(doc_lens)) if doc_lens else 0.0

        return {
            "bm25": {
                "k1": 1.5,
                "b": 0.75,
                "doc_count": len(chunk_records),
                "avg_doc_len": avg_doc_len,
                "doc_freq": doc_freq,
                "doc_lens": doc_lens,
                "term_freqs": term_freqs,
                "ids": ids,
            }
        }

    def _load_manifest(self) -> dict[str, Any]:
        if not self._is_local_enabled:
            return {"documents": {}}

        if not self.manifest_path.exists():
            return {"documents": {}}

        with self.manifest_path.open("r", encoding="utf-8") as file:
            try:
                parsed = json.load(file)
            except json.JSONDecodeError:
                return {"documents": {}}

        if not isinstance(parsed, dict) or not isinstance(parsed.get("documents"), dict):
            return {"documents": {}}

        return parsed

    def _save_manifest_entry(self, document_id: str, chunk_count: int, vector_count: int) -> None:
        if not self._is_local_enabled:
            return

        manifest = self._load_manifest()
        manifest["documents"][document_id] = {
            "document_path": f"documents/{document_id}.json",
            "vectors_path": f"vectors/{document_id}.npy",
            "vector_meta_path": f"vectors/{document_id}_meta.json",
            "keyword_path": f"keyword/{document_id}_bm25.json",
            "chunk_count": chunk_count,
            "vector_count": vector_count,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        with self.manifest_path.open("w", encoding="utf-8") as file:
            json.dump(manifest, file, ensure_ascii=True, indent=2)

    def _passes_filter(self, item: dict[str, Any], filters: dict[str, Any] | None) -> bool:
        if not filters:
            return True

        for key, expected in filters.items():
            actual = item.get(key)
            if isinstance(expected, (list, tuple, set)):
                if actual not in expected:
                    return False
            else:
                if actual != expected:
                    return False

        return True

    def _bm25_score(self, query_tokens: list[str], keyword_index: dict[str, Any]) -> dict[str, float]:
        bm25 = keyword_index.get("bm25", {})
        k1 = float(bm25.get("k1", 1.5))
        b = float(bm25.get("b", 0.75))
        n_docs = int(bm25.get("doc_count", 0))
        avg_doc_len = float(bm25.get("avg_doc_len", 0.0))
        doc_freq = bm25.get("doc_freq", {})
        doc_lens = bm25.get("doc_lens", [])
        term_freqs = bm25.get("term_freqs", [])
        ids = bm25.get("ids", [])

        scores: dict[str, float] = {}
        if n_docs == 0 or avg_doc_len == 0.0:
            return scores

        for i, chunk_id in enumerate(ids):
            tf = term_freqs[i]
            doc_len = float(doc_lens[i]) if i < len(doc_lens) else 0.0
            score = 0.0

            for token in query_tokens:
                df = int(doc_freq.get(token, 0))
                if df == 0:
                    continue

                idf = math.log(1.0 + ((n_docs - df + 0.5) / (df + 0.5)))
                term_count = float(tf.get(token, 0))
                if term_count == 0.0:
                    continue

                denom = term_count + k1 * (1.0 - b + b * (doc_len / avg_doc_len))
                score += idf * ((term_count * (k1 + 1.0)) / denom)

            scores[chunk_id] = score

        return scores

    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Index one processed document into vector, keyword, and metadata stores."""

        document_id = self._stable_document_id(payload)
        document_record = self._build_document_record(payload, document_id)
        chunk_records = self._build_chunk_records(payload, document_id)

        vector_matrix, vector_meta = self._build_vector_index(chunk_records)
        keyword_index = self._build_keyword_index(chunk_records)

        result: dict[str, Any] = {
            "document_id": document_id,
            "index_status": "indexed",
            "storage_mode": self.storage_mode,
            "chunk_count": len(chunk_records),
            "vector_count": int(vector_matrix.shape[0]),
        }

        if self._is_local_enabled:
            document_path = self.documents_dir / f"{document_id}.json"
            vectors_path = self.vectors_dir / f"{document_id}.npy"
            vector_meta_path = self.vectors_dir / f"{document_id}_meta.json"
            keyword_path = self.keyword_dir / f"{document_id}_bm25.json"

            with document_path.open("w", encoding="utf-8") as file:
                json.dump({"document": document_record, "chunks": chunk_records}, file, ensure_ascii=True, indent=2)

            np.save(vectors_path, vector_matrix)

            with vector_meta_path.open("w", encoding="utf-8") as file:
                json.dump(vector_meta, file, ensure_ascii=True, indent=2)

            with keyword_path.open("w", encoding="utf-8") as file:
                json.dump(keyword_index, file, ensure_ascii=True, indent=2)

            self._save_manifest_entry(
                document_id=document_id,
                chunk_count=len(chunk_records),
                vector_count=int(vector_matrix.shape[0]),
            )

            result.update(
                {
                    "document_path": str(document_path),
                    "vectors_path": str(vectors_path),
                    "vector_meta_path": str(vector_meta_path),
                    "keyword_path": str(keyword_path),
                }
            )

        if self._is_vectordb_enabled:
            if self.vector_db_client is None:
                raise ValueError(
                    "storage_mode requires vector_db_client for vectordb uploads. "
                    "Pass a client that implements upsert_document(...)."
                )

            upload_result = self.vector_db_client.upsert_document(
                document=document_record,
                chunks=chunk_records,
                vectors=vector_matrix,
                vector_metadata=vector_meta,
                keyword_index=keyword_index,
            )
            result["vectordb_upload"] = upload_result if isinstance(upload_result, dict) else {"status": "ok"}

        return result

    def vector_search(
        self,
        query_embedding: list[float],
        document_id: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if not self._is_local_enabled:
            raise ValueError("vector_search is only available when local storage is enabled.")

        vectors_path = self.vectors_dir / f"{document_id}.npy"
        vector_meta_path = self.vectors_dir / f"{document_id}_meta.json"

        if not vectors_path.exists() or not vector_meta_path.exists() or not query_embedding:
            return []

        matrix = np.load(vectors_path)
        with vector_meta_path.open("r", encoding="utf-8") as file:
            metadata = json.load(file)

        if matrix.size == 0 or not isinstance(metadata, list):
            return []

        query = np.asarray(query_embedding, dtype=np.float32)
        if query.ndim != 1 or query.shape[0] != matrix.shape[1]:
            return []

        query_norm = np.linalg.norm(query)
        matrix_norm = np.linalg.norm(matrix, axis=1)
        denominator = np.clip(matrix_norm * query_norm, a_min=1e-8, a_max=None)
        similarities = np.dot(matrix, query) / denominator

        ranked = np.argsort(-similarities)
        results: list[dict[str, Any]] = []

        for idx in ranked:
            item = metadata[int(idx)]
            if not self._passes_filter(item, filters):
                continue

            results.append(
                {
                    "document_id": item.get("document_id"),
                    "chunk_id": item.get("chunk_id"),
                    "chunk_index": item.get("chunk_index"),
                    "text": item.get("text"),
                    "workspace_id": item.get("workspace_id"),
                    "owner_user_id": item.get("owner_user_id"),
                    "timecode": item.get("timecode"),
                    "topic": item.get("topic"),
                    "difficulty": item.get("difficulty"),
                    "speaker": item.get("speaker"),
                    "score": float(similarities[int(idx)]),
                    "search_type": "vector",
                }
            )

            if len(results) >= top_k:
                break

        return results

    def keyword_search(
        self,
        query_text: str,
        document_id: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if not self._is_local_enabled:
            raise ValueError("keyword_search is only available when local storage is enabled.")

        keyword_path = self.keyword_dir / f"{document_id}_bm25.json"
        document_path = self.documents_dir / f"{document_id}.json"

        if not keyword_path.exists() or not document_path.exists() or not query_text.strip():
            return []

        with keyword_path.open("r", encoding="utf-8") as file:
            keyword_index = json.load(file)
        with document_path.open("r", encoding="utf-8") as file:
            document_data = json.load(file)

        chunks = document_data.get("chunks", []) if isinstance(document_data, dict) else []
        by_key = {
            f"{chunk.get('document_id')}::{chunk.get('chunk_id')}": chunk
            for chunk in chunks
            if isinstance(chunk, dict)
        }

        query_tokens = self._tokenize(query_text)
        scores = self._bm25_score(query_tokens, keyword_index)
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)

        results: list[dict[str, Any]] = []
        for compound_id, score in ranked:
            chunk = by_key.get(compound_id)
            if not chunk or not self._passes_filter(chunk, filters):
                continue

            results.append(
                {
                    "document_id": chunk.get("document_id"),
                    "chunk_id": chunk.get("chunk_id"),
                    "chunk_index": chunk.get("chunk_index"),
                    "text": chunk.get("text"),
                    "workspace_id": chunk.get("workspace_id"),
                    "owner_user_id": chunk.get("owner_user_id"),
                    "timecode": chunk.get("timecode"),
                    "topic": chunk.get("topic"),
                    "difficulty": chunk.get("difficulty"),
                    "speaker": chunk.get("speaker"),
                    "score": float(score),
                    "search_type": "keyword",
                }
            )

            if len(results) >= top_k:
                break

        return results

    def hybrid_search(
        self,
        query_text: str,
        query_embedding: list[float],
        document_id: str,
        top_k: int = 5,
        alpha: float = 0.5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Hybrid retrieval combining vector and BM25 scores."""

        alpha = min(max(alpha, 0.0), 1.0)
        vector_results = self.vector_search(
            query_embedding=query_embedding,
            document_id=document_id,
            top_k=max(top_k * 4, 10),
            filters=filters,
        )
        keyword_results = self.keyword_search(
            query_text=query_text,
            document_id=document_id,
            top_k=max(top_k * 4, 10),
            filters=filters,
        )

        vector_scores = {str(item.get("chunk_id")): float(item.get("score", 0.0)) for item in vector_results}
        keyword_scores = {str(item.get("chunk_id")): float(item.get("score", 0.0)) for item in keyword_results}

        all_ids = set(vector_scores.keys()) | set(keyword_scores.keys())
        if not all_ids:
            return []

        max_vector = max(vector_scores.values()) if vector_scores else 1.0
        max_keyword = max(keyword_scores.values()) if keyword_scores else 1.0
        if max_vector == 0.0:
            max_vector = 1.0
        if max_keyword == 0.0:
            max_keyword = 1.0

        item_ref: dict[str, dict[str, Any]] = {}
        for item in vector_results + keyword_results:
            item_ref[str(item.get("chunk_id"))] = item

        merged: list[dict[str, Any]] = []
        for chunk_id in all_ids:
            v = vector_scores.get(chunk_id, 0.0) / max_vector
            k = keyword_scores.get(chunk_id, 0.0) / max_keyword
            hybrid = alpha * v + (1.0 - alpha) * k

            base_item = dict(item_ref.get(chunk_id, {}))
            base_item["score"] = float(hybrid)
            base_item["vector_score"] = float(vector_scores.get(chunk_id, 0.0))
            base_item["keyword_score"] = float(keyword_scores.get(chunk_id, 0.0))
            base_item["search_type"] = "hybrid"
            merged.append(base_item)

        merged.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
        return merged[:top_k]

