from __future__ import annotations

import uuid

import structlog
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.qa_pair import QAPair

logger = structlog.get_logger()


async def search_qa(db: AsyncSession, query: str) -> QAPair | None:
    """
    双向模糊匹配：
    1. 问题字段整体 ILIKE
    2. 按词分词 OR-ILIKE + 关键词加权
    命中后返回得分最高的一条，未命中返回 None。
    """
    q = query.strip()
    if len(q) < 2:
        return None

    # 整体 ILIKE（问题包含用户输入）
    result = await db.execute(
        select(QAPair).where(
            QAPair.is_active.is_(True),
            QAPair.deleted_at.is_(None),
            QAPair.question.ilike(f"%{q}%"),
        )
        .order_by(QAPair.updated_at.desc())
        .limit(1)
    )
    hit = result.scalar_one_or_none()
    if hit:
        logger.info("qa_hit_exact", qa_id=str(hit.id))
        return hit

    # 分词 OR-ILIKE
    words = [w for w in q.split() if len(w) >= 2]
    if not words:
        return None

    conditions = [QAPair.question.ilike(f"%{w}%") for w in words]
    result2 = await db.execute(
        select(QAPair).where(
            QAPair.is_active.is_(True),
            QAPair.deleted_at.is_(None),
            or_(*conditions),
        )
        .limit(10)
    )
    candidates = list(result2.scalars().all())
    if not candidates:
        return None

    # 关键词加权打分，选得分最高的
    best: QAPair | None = None
    best_score = 0
    ql = q.lower()
    for pair in candidates:
        score = sum(1 for w in words if w.lower() in pair.question.lower())
        score += sum(2 for kw in (pair.keywords or []) if kw and kw.lower() in ql)
        if score > best_score:
            best_score = score
            best = pair

    if best:
        logger.info("qa_hit_fuzzy", qa_id=str(best.id), score=best_score)
    return best


async def list_qa(
    db: AsyncSession,
    search: str | None = None,
    category: str | None = None,
    include_inactive: bool = False,
    limit: int = 100,
) -> list[QAPair]:
    stmt = (
        select(QAPair)
        .where(QAPair.deleted_at.is_(None))
        .order_by(QAPair.updated_at.desc())
        .limit(limit)
    )
    if not include_inactive:
        stmt = stmt.where(QAPair.is_active.is_(True))
    if search:
        stmt = stmt.where(
            or_(QAPair.question.ilike(f"%{search}%"), QAPair.answer.ilike(f"%{search}%"))
        )
    if category:
        stmt = stmt.where(QAPair.category == category)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_qa(
    db: AsyncSession,
    question: str,
    answer: str,
    keywords: list[str] | None = None,
    category: str | None = None,
) -> QAPair:
    pair = QAPair(
        question=question.strip(),
        answer=answer.strip(),
        keywords=keywords or [],
        category=category,
    )
    db.add(pair)
    await db.commit()
    await db.refresh(pair)
    return pair


async def update_qa(
    db: AsyncSession,
    qa_id: uuid.UUID,
    **kwargs: object,
) -> QAPair:
    result = await db.execute(
        select(QAPair).where(QAPair.id == qa_id, QAPair.deleted_at.is_(None))
    )
    pair = result.scalar_one_or_none()
    if not pair:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(f"QAPair {qa_id} not found")
    for k, v in kwargs.items():
        setattr(pair, k, v)
    db.add(pair)
    await db.commit()
    await db.refresh(pair)
    return pair


async def delete_qa(db: AsyncSession, qa_id: uuid.UUID) -> None:
    from datetime import datetime, timezone
    result = await db.execute(
        select(QAPair).where(QAPair.id == qa_id, QAPair.deleted_at.is_(None))
    )
    pair = result.scalar_one_or_none()
    if not pair:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(f"QAPair {qa_id} not found")
    pair.deleted_at = datetime.now(timezone.utc)
    db.add(pair)
    await db.commit()


async def batch_import(
    db: AsyncSession,
    items: list[dict[str, object]],
) -> int:
    """批量导入，返回成功条数。"""
    count = 0
    for item in items:
        q = str(item.get("question", "")).strip()
        a = str(item.get("answer", "")).strip()
        if not q or not a:
            continue
        pair = QAPair(
            question=q,
            answer=a,
            keywords=item.get("keywords") or [],
            category=str(item["category"]) if item.get("category") else None,
        )
        db.add(pair)
        count += 1
    if count:
        await db.commit()
    return count
