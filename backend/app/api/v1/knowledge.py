from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.exceptions import ValidationError
from app.database import get_db
from app.models.staff import Staff
from app.schemas.knowledge import CollectionCreate, CollectionResponse, DocumentUploadResponse
from app.services import rag_service

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

_ALLOWED = {".pdf", ".txt", ".md"}
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(get_current_user),
) -> DocumentUploadResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED:
        raise ValidationError(f"Unsupported file type: {suffix}. Allowed: pdf, txt, md")
    content_bytes = await file.read()
    if len(content_bytes) > _MAX_UPLOAD_BYTES:
        raise ValidationError("文件大小超过 10 MB 限制")
    file_type = suffix.lstrip(".")
    text = rag_service.extract_text(content_bytes, file_type)
    collection = await rag_service.get_or_create_default_collection(db)
    doc = await rag_service.create_document(
        db, collection.id, file.filename or "unknown", text, file_type
    )
    await rag_service.process_document_chunks(db, doc.id)
    return DocumentUploadResponse.model_validate(doc)


@router.get("/search")
async def search_knowledge(
    q: str = Query(..., min_length=1),
    top_k: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(get_current_user),
) -> dict[str, list[dict[str, object]]]:
    results = await rag_service.search_chunks(db, q, top_k)
    return {"results": results}


# ── Collections CRUD ──────────────────────────────────────────────────────────


@router.get("/collections", response_model=list[CollectionResponse])
async def list_collections(
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(get_current_user),
) -> list[CollectionResponse]:
    colls = await rag_service.list_collections(db)
    return [CollectionResponse.model_validate(c) for c in colls]


@router.post("/collections", response_model=CollectionResponse, status_code=201)
async def create_collection(
    data: CollectionCreate,
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(get_current_user),
) -> CollectionResponse:
    coll = await rag_service.create_collection(db, data.name, data.description)
    return CollectionResponse.model_validate(coll)


@router.delete("/collections/{collection_id}", status_code=204)
async def delete_collection(
    collection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(get_current_user),
) -> Response:
    await rag_service.delete_collection(db, collection_id)
    return Response(status_code=204)


# ── Documents CRUD ────────────────────────────────────────────────────────────


@router.get("/documents", response_model=list[DocumentUploadResponse])
async def list_documents(
    collection_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(get_current_user),
) -> list[DocumentUploadResponse]:
    docs = await rag_service.list_documents(db, collection_id)
    return [DocumentUploadResponse.model_validate(d) for d in docs]


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(get_current_user),
) -> Response:
    await rag_service.delete_document(db, document_id)
    return Response(status_code=204)
