from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeChunk, KnowledgeCollection, KnowledgeDocument

logger = structlog.get_logger()

_DEFAULT_COLLECTION_NAME = "默认知识库"


async def get_or_create_default_collection(db: AsyncSession) -> KnowledgeCollection:
    result = await db.execute(
        select(KnowledgeCollection).where(
            KnowledgeCollection.name == _DEFAULT_COLLECTION_NAME,
            KnowledgeCollection.deleted_at.is_(None),
        )
    )
    coll = result.scalar_one_or_none()
    if not coll:
        coll = KnowledgeCollection(name=_DEFAULT_COLLECTION_NAME)
        db.add(coll)
        await db.commit()
        await db.refresh(coll)
    return coll


def extract_text(content: bytes, file_type: str) -> str:
    if file_type in ("txt", "md"):
        return content.decode("utf-8", errors="replace")
    if file_type == "pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(content))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages).strip()
        except Exception as e:
            logger.warning("pdf_extract_failed", error=str(e))
            return ""
    return ""


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    if not text.strip():
        return []
    chunks: list[str] = []
    start = 0
    step = max(1, chunk_size - overlap)
    while start < len(text):
        chunk = text[start : start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks


async def embed_text(text: str) -> list[float]:
    from app.config import settings

    headers: dict[str, str] = {}
    if settings.embedding_api_key:
        headers["Authorization"] = f"Bearer {settings.embedding_api_key}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{settings.embedding_base_url}/embeddings",
            json={"input": text, "model": settings.embedding_model},
            headers=headers,
        )
        resp.raise_for_status()
        return list(resp.json()["data"][0]["embedding"])


async def process_document_chunks(db: AsyncSession, doc_id: uuid.UUID) -> int:
    result = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if not doc or not doc.content:
        return 0

    chunks = chunk_text(doc.content)
    for idx, chunk_content in enumerate(chunks):
        try:
            vector = await embed_text(chunk_content)
        except Exception as e:
            logger.warning("embed_failed", chunk_index=idx, error=str(e))
            vector = None

        chunk = KnowledgeChunk(
            collection_id=doc.collection_id,
            document_name=doc.filename,
            chunk_index=idx,
            content=chunk_content,
            embedding=vector,
        )
        db.add(chunk)

    await db.commit()
    return len(chunks)


async def search_chunks(
    db: AsyncSession, query: str, top_k: int = 5
) -> list[dict[str, object]]:
    try:
        from pgvector.sqlalchemy import Vector
        from sqlalchemy import cast, func

        query_vector = await embed_text(query)
        q_cast = cast(query_vector, Vector(1536))
        distance_col = func.cosine_distance(KnowledgeChunk.embedding, q_cast).label("score")
        stmt = (
            select(KnowledgeChunk, distance_col)
            .where(KnowledgeChunk.embedding.isnot(None), KnowledgeChunk.deleted_at.is_(None))
            .order_by(distance_col)
            .limit(top_k)
        )
        rows = (await db.execute(stmt)).all()
        return [
            {
                "id": str(row.KnowledgeChunk.id),
                "document_name": row.KnowledgeChunk.document_name,
                "content": row.KnowledgeChunk.content,
                "score": round(1.0 - float(row.score), 4) if row.score is not None else 0.0,
            }
            for row in rows
        ]
    except Exception as e:
        logger.warning("vector_search_failed_fallback_text", error=str(e))
        stmt2 = (
            select(KnowledgeChunk)
            .where(
                KnowledgeChunk.content.ilike(f"%{query}%"),
                KnowledgeChunk.deleted_at.is_(None),
            )
            .limit(top_k)
        )
        return [
            {
                "id": str(c.id),
                "document_name": c.document_name,
                "content": c.content,
                "score": 1.0,
            }
            for c in (await db.execute(stmt2)).scalars().all()
        ]


async def create_document(
    db: AsyncSession,
    collection_id: object,
    filename: str,
    content: str,
    file_type: str,
) -> KnowledgeDocument:
    doc = KnowledgeDocument(
        collection_id=collection_id,
        filename=filename,
        file_type=file_type,
        content=content,
        status="done" if content else "pending",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def list_collections(db: AsyncSession) -> list[KnowledgeCollection]:
    result = await db.execute(
        select(KnowledgeCollection)
        .where(KnowledgeCollection.deleted_at.is_(None))
        .order_by(KnowledgeCollection.created_at)
    )
    return list(result.scalars().all())


async def create_collection(
    db: AsyncSession, name: str, description: str | None = None
) -> KnowledgeCollection:
    coll = KnowledgeCollection(name=name, description=description)
    db.add(coll)
    await db.commit()
    await db.refresh(coll)
    return coll


async def delete_collection(db: AsyncSession, collection_id: uuid.UUID) -> None:
    result = await db.execute(
        select(KnowledgeCollection).where(KnowledgeCollection.id == collection_id)
    )
    coll = result.scalar_one_or_none()
    if coll:
        coll.deleted_at = datetime.now(UTC)
        await db.commit()


async def list_documents(
    db: AsyncSession, collection_id: uuid.UUID | None = None
) -> list[KnowledgeDocument]:
    stmt = select(KnowledgeDocument).where(KnowledgeDocument.deleted_at.is_(None))
    if collection_id:
        stmt = stmt.where(KnowledgeDocument.collection_id == collection_id)
    result = await db.execute(stmt.order_by(KnowledgeDocument.created_at))
    return list(result.scalars().all())


async def delete_document(db: AsyncSession, document_id: uuid.UUID) -> None:
    result = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if doc:
        doc.deleted_at = datetime.now(UTC)
        await db.commit()
