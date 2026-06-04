"""Qdrant client wrapper: per-workspace collections, upsert, search, delete."""
from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qm
from qdrant_client.http.exceptions import UnexpectedResponse

from app.core.config import settings

log = structlog.get_logger(__name__)

VECTOR_SIZE = 1536
DISTANCE = qm.Distance.COSINE


class QdrantService:
    def __init__(self) -> None:
        self.client = AsyncQdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)

    @staticmethod
    def collection_name(workspace_id: UUID) -> str:
        return f"ws_{workspace_id.hex}_vectors"

    async def ensure_collection(self, workspace_id: UUID) -> None:
        name = self.collection_name(workspace_id)
        try:
            await self.client.get_collection(name)
        except UnexpectedResponse:
            await self.client.create_collection(
                collection_name=name,
                vectors_config=qm.VectorParams(size=VECTOR_SIZE, distance=DISTANCE),
                optimizers_config=qm.OptimizersConfigDiff(default_segment_number=2),
            )
            await self.client.create_payload_index(
                collection_name=name,
                field_name="workspace_id",
                field_schema=qm.PayloadSchemaType.KEYWORD,
            )
            await self.client.create_payload_index(
                collection_name=name, field_name="website_id", field_schema=qm.PayloadSchemaType.KEYWORD
            )
            await self.client.create_payload_index(
                collection_name=name, field_name="page_id", field_schema=qm.PayloadSchemaType.KEYWORD
            )

    async def upsert_chunks(self, workspace_id: UUID, chunks: list[dict]) -> None:
        await self.ensure_collection(workspace_id)
        name = self.collection_name(workspace_id)
        points = [
            qm.PointStruct(
                id=str(c["qdrant_point_id"]),
                vector=c["vector"],
                payload={
                    "workspace_id": str(workspace_id),
                    "website_id": str(c["website_id"]),
                    "page_id": str(c["page_id"]),
                    "chunk_id": str(c["id"]),
                    "source_url": c.get("source_url", ""),
                    "title": c.get("title", ""),
                    "heading_context": c.get("heading_context"),
                    "content": c["content"],
                    "token_count": c["token_count"],
                    "chunk_index": c["chunk_index"],
                    "created_at": c.get("created_at"),
                },
            )
            for c in chunks
        ]
        for i in range(0, len(points), 100):
            await self.client.upsert(collection_name=name, points=points[i : i + 100], wait=True)

    async def search(
        self,
        workspace_id: UUID,
        query_vector: list[float],
        *,
        top_k: int = 8,
        score_threshold: float = 0.72,
        website_id: UUID | None = None,
    ) -> list[dict]:
        await self.ensure_collection(workspace_id)
        name = self.collection_name(workspace_id)

        flt = [qm.FieldCondition(key="workspace_id", match=qm.MatchValue(value=str(workspace_id)))]
        if website_id:
            flt.append(qm.FieldCondition(key="website_id", match=qm.MatchValue(value=str(website_id))))

        results = await self.client.query_points(
            collection_name=name,
            query=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
            query_filter=qm.Filter(must=flt),
        )
        return [
            {
                "id": str(hit.id),
                "score": hit.score,
                **hit.payload,
            }
            for hit in results.points
        ]

    async def delete_by_website(self, workspace_id: UUID, website_id: UUID) -> None:
        name = self.collection_name(workspace_id)
        try:
            await self.client.delete(
                collection_name=name,
                points_selector=qm.FilterSelector(
                    filter=qm.Filter(
                        must=[
                            qm.FieldCondition(key="workspace_id", match=qm.MatchValue(value=str(workspace_id))),
                            qm.FieldCondition(key="website_id", match=qm.MatchValue(value=str(website_id))),
                        ]
                    )
                ),
            )
        except UnexpectedResponse:
            pass

    async def delete_collection(self, workspace_id: UUID) -> None:
        name = self.collection_name(workspace_id)
        try:
            await self.client.delete_collection(name)
        except UnexpectedResponse:
            pass

    async def get_collection_info(self, workspace_id: UUID) -> dict[str, Any]:
        name = self.collection_name(workspace_id)
        try:
            info = await self.client.get_collection(name)
            return {
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status.value if info.status else None,
            }
        except UnexpectedResponse:
            return {"vectors_count": 0, "points_count": 0, "status": "missing"}
