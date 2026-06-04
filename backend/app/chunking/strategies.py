"""Three chunking strategies: recursive, semantic, fixed-size."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable
from uuid import UUID, uuid4

import structlog
import tiktoken

log = structlog.get_logger(__name__)

DEFAULT_ENCODER = "cl100k_base"

RECURSIVE_SEPARATORS = ["\n\n", "\n", ". ", " "]


def _encoder() -> "tiktoken.Encoding":
    return tiktoken.get_encoding(DEFAULT_ENCODER)


def count_tokens(text: str) -> int:
    return len(_encoder().encode(text))


@dataclass(slots=True)
class Chunk:
    content: str
    token_count: int
    heading_context: str | None = None
    chunk_index: int = 0
    total_chunks_in_page: int = 0


def _split_recursive(text: str, chunk_size: int, overlap: int) -> list[str]:
    enc = _encoder()

    def token_len(s: str) -> int:
        return len(enc.encode(s))

    def merge(pieces: list[str], seps: list[str]) -> list[str]:
        if not seps:
            return pieces
        sep = seps[0]
        out: list[str] = []
        for piece in pieces:
            out.extend(piece.split(sep))
        return [p for p in out if p.strip()]

    pieces = [text]
    for sep in RECURSIVE_SEPARATORS:
        new_pieces: list[str] = []
        for p in pieces:
            if token_len(p) <= chunk_size:
                new_pieces.append(p)
            else:
                new_pieces.extend(p.split(sep))
        pieces = [p.strip() for p in new_pieces if p and p.strip()]

    chunks: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for p in pieces:
        plen = token_len(p)
        if cur_len + plen > chunk_size and cur:
            chunks.append(" ".join(cur))
            tail = " ".join(cur)
            if overlap > 0 and len(tail) > 0:
                tail_tokens = enc.encode(tail)
                keep = tail_tokens[-overlap:]
                cur = [enc.decode(keep)]
                cur_len = len(keep)
            else:
                cur, cur_len = [], 0
        cur.append(p)
        cur_len += plen
    if cur:
        chunks.append(" ".join(cur))
    return chunks


def _heading_for_position(text: str, pos: int) -> str | None:
    """Find the nearest h1/h2 above the chunk start in flat text."""
    head = text[:pos]
    h1 = list(re.finditer(r"^# .+$", head, re.MULTILINE))
    h2 = list(re.finditer(r"^## .+$", head, re.MULTILINE))
    if not (h1 or h2):
        return None
    last_h1 = h1[-1].group(0).lstrip("# ").strip() if h1 else ""
    last_h2 = h2[-1].group(0).lstrip("# ").strip() if h2 else ""
    parts = [p for p in (last_h1, last_h2) if p]
    return " > ".join(parts) if parts else None


def chunk_recursive(
    text: str,
    *,
    chunk_size: int = 512,
    overlap: int = 64,
) -> list[Chunk]:
    if not text.strip():
        return []
    pieces = _split_recursive(text, chunk_size, overlap)
    out: list[Chunk] = []
    pos = 0
    for idx, p in enumerate(pieces):
        idx_in_text = text.find(p[:80], pos)
        heading = _heading_for_position(text, idx_in_text) if idx_in_text >= 0 else None
        out.append(
            Chunk(
                content=p,
                token_count=count_tokens(p),
                heading_context=heading,
                chunk_index=idx,
            )
        )
        pos = idx_in_text + len(p) if idx_in_text >= 0 else pos + len(p)
    for c in out:
        c.total_chunks_in_page = len(out)
    return out


def chunk_fixed(text: str, *, chunk_size: int = 512, overlap: int = 64) -> list[Chunk]:
    if not text.strip():
        return []
    enc = _encoder()
    tokens = enc.encode(text)
    out: list[Chunk] = []
    start = 0
    idx = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        piece = enc.decode(tokens[start:end])
        out.append(Chunk(content=piece, token_count=end - start, chunk_index=idx))
        start = end - overlap if end < len(tokens) else end
        idx += 1
    for c in out:
        c.total_chunks_in_page = len(out)
    return out


async def chunk_semantic(
    text: str,
    *,
    embed_fn,
    chunk_size: int = 512,
    similarity_threshold: float = 0.85,
) -> list[Chunk]:
    """Group sentences by cosine similarity > threshold using embed_fn(sentences) -> list[list[float]]."""
    if not text.strip():
        return []
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if not sentences:
        return []
    embeddings = await embed_fn(sentences)
    import numpy as np

    sim = np.dot(embeddings, np.array(embeddings).T)
    norm = np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-9
    sim = sim / (norm @ norm.T)

    out: list[Chunk] = []
    buf: list[str] = []
    buf_tokens = 0
    for i, sent in enumerate(sentences):
        s_tokens = count_tokens(sent)
        if buf and (sim[i - 1, i] < similarity_threshold or buf_tokens + s_tokens > chunk_size):
            out.append(Chunk(content=" ".join(buf), token_count=buf_tokens, chunk_index=len(out)))
            buf, buf_tokens = [], 0
        buf.append(sent)
        buf_tokens += s_tokens
    if buf:
        out.append(Chunk(content=" ".join(buf), token_count=buf_tokens, chunk_index=len(out)))
    for c in out:
        c.total_chunks_in_page = len(out)
    return out


class ChunkingService:
    def __init__(self, *, strategy: str = "recursive", chunk_size: int = 512, overlap: int = 64) -> None:
        self.strategy = strategy
        self.chunk_size = chunk_size
        self.overlap = overlap

    async def split(self, text: str, embed_fn=None) -> list[Chunk]:
        if self.strategy == "semantic":
            if embed_fn is None:
                raise ValueError("semantic strategy requires embed_fn")
            return await chunk_semantic(text, embed_fn=embed_fn, chunk_size=self.chunk_size)
        if self.strategy == "fixed":
            return chunk_fixed(text, chunk_size=self.chunk_size, overlap=self.overlap)
        return chunk_recursive(text, chunk_size=self.chunk_size, overlap=self.overlap)

    def to_db_records(
        self,
        chunks: Iterable[Chunk],
        *,
        page_id: UUID,
        website_id: UUID,
        workspace_id: UUID,
        embedding_model: str,
        embedding_dim: int = 1536,
    ) -> list[dict]:
        return [
            {
                "id": uuid4(),
                "page_id": page_id,
                "website_id": website_id,
                "workspace_id": workspace_id,
                "content": c.content,
                "token_count": c.token_count,
                "chunk_index": c.chunk_index,
                "total_chunks_in_page": c.total_chunks_in_page,
                "heading_context": c.heading_context,
                "embedding_model": embedding_model,
                "embedding_dim": embedding_dim,
                "qdrant_point_id": uuid4(),
            }
            for c in chunks
        ]
