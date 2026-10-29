from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable

import numpy as np
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parents[1]
DOC_DIR = ROOT / "data" / "documents"
CACHE_DIR = ROOT / "data" / "index"


@dataclass
class Chunk:
    source: str
    text: str
    page: int | None = None

    def to_dict(self) -> dict:
        return {"source": self.source, "text": self.text, "page": self.page}


def _chunk_text(text: str, source: str, page: int | None, chunk_size: int = 1200, overlap: int = 180) -> list[Chunk]:
    clean = " ".join(text.split())
    if not clean:
        return []
    chunks: list[Chunk] = []
    start = 0
    while start < len(clean):
        end = min(len(clean), start + chunk_size)
        chunks.append(Chunk(source=source, page=page, text=clean[start:end]))
        if end == len(clean):
            break
        start = max(0, end - overlap)
    return chunks


def load_chunks(doc_dir: Path = DOC_DIR) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(doc_dir.glob("*")):
        if path.suffix.lower() in {".md", ".txt"}:
            chunks.extend(_chunk_text(path.read_text(encoding="utf-8", errors="ignore"), path.name, None))
        elif path.suffix.lower() == ".pdf":
            reader = PdfReader(str(path))
            for page_no, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                chunks.extend(_chunk_text(text, path.name, page_no))
    return chunks


class LocalTfidfRetriever:
    """Offline retrieval baseline: sparse vectors + cosine similarity."""

    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=15000)
        corpus = [c.text for c in chunks] or [""]
        self.matrix = self.vectorizer.fit_transform(corpus)

    def search(self, query: str, top_k: int = 4) -> list[dict]:
        if not self.chunks:
            return []
        q = self.vectorizer.transform([query])
        scores = cosine_similarity(q, self.matrix)[0]
        order = np.argsort(scores)[::-1][:top_k]
        return [
            {**self.chunks[i].to_dict(), "score": round(float(scores[i]), 4)}
            for i in order
            if scores[i] > 0
        ]


class OpenAIEmbeddingRetriever:
    """Dense-vector retrieval using OpenAI embeddings, with a small local cache."""

    def __init__(self, chunks: list[Chunk], model: str = "text-embedding-3-small"):
        from openai import OpenAI

        self.client = OpenAI()
        self.model = model
        self.chunks = chunks
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.embeddings = self._load_or_build_embeddings()

    def _cache_key(self) -> str:
        digest = hashlib.sha256()
        digest.update(self.model.encode())
        for chunk in self.chunks:
            digest.update(chunk.source.encode())
            digest.update(chunk.text.encode())
        return digest.hexdigest()[:16]

    def _load_or_build_embeddings(self) -> np.ndarray:
        key = self._cache_key()
        arr_path = CACHE_DIR / f"embeddings_{key}.npy"
        meta_path = CACHE_DIR / f"embeddings_{key}.json"
        if arr_path.exists() and meta_path.exists():
            return np.load(arr_path)

        texts = [c.text.replace("\n", " ") for c in self.chunks]
        vectors: list[list[float]] = []
        batch_size = 64
        for i in range(0, len(texts), batch_size):
            response = self.client.embeddings.create(model=self.model, input=texts[i:i + batch_size])
            vectors.extend(item.embedding for item in response.data)
        matrix = np.asarray(vectors, dtype=float)
        np.save(arr_path, matrix)
        meta_path.write_text(json.dumps({"model": self.model, "chunks": len(self.chunks)}, indent=2))
        return matrix

    def search(self, query: str, top_k: int = 4) -> list[dict]:
        if not self.chunks:
            return []
        response = self.client.embeddings.create(model=self.model, input=[query.replace("\n", " ")])
        q = np.asarray(response.data[0].embedding, dtype=float)
        denom = (np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(q)) + 1e-12
        scores = (self.embeddings @ q) / denom
        order = np.argsort(scores)[::-1][:top_k]
        return [
            {**self.chunks[i].to_dict(), "score": round(float(scores[i]), 4)}
            for i in order
        ]


def build_retriever(prefer_embeddings: bool | None = None):
    chunks = load_chunks()
    if prefer_embeddings is None:
        prefer_embeddings = os.getenv("USE_OPENAI_EMBEDDINGS", "false").lower() == "true"
    if prefer_embeddings and os.getenv("OPENAI_API_KEY"):
        try:
            return OpenAIEmbeddingRetriever(chunks)
        except Exception:
            # The prototype remains usable if the remote embedding service is unavailable.
            pass
    return LocalTfidfRetriever(chunks)
