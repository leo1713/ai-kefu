"""conversation_service 单元测试。

所有测试都 mock 数据库，不需要真实 PostgreSQL。
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── helpers ───────────────────────────────────────────────────────────────────


def _make_conv(
    status: str = "active",
    assigned_staff_id: uuid.UUID | None = None,
    transfer_reason: str | None = None,
) -> MagicMock:
    conv = MagicMock()
    conv.id = uuid.uuid4()
    conv.visitor_id = uuid.uuid4()
    conv.status = status
    conv.assigned_staff_id = assigned_staff_id
    conv.transfer_reason = transfer_reason
    return conv


def _make_staff(is_active: bool = True) -> MagicMock:
    staff = MagicMock()
    staff.id = uuid.uuid4()
    staff.username = "staff01"
    staff.display_name = "张客服"
    staff.is_active = is_active
    staff.deleted_at = None
    return staff


def _make_db(query_result: object | None = None, all_results: list[object] | None = None) -> AsyncMock:
    """构造最小化的 AsyncSession mock。"""
    db = AsyncMock()
    db.add = MagicMock()

    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none = MagicMock(return_value=query_result)

    scalars_result = MagicMock()
    scalars_result.scalars = MagicMock(
        return_value=MagicMock(
            all=MagicMock(return_value=all_results or [])
        )
    )
    scalars_result.all = MagicMock(return_value=all_results or [])

    db.execute = AsyncMock(return_value=scalar_result)
    return db


# ── transfer_conversation ──────────────────────────────────────────────────────


async def test_transfer_conversation_updates_status() -> None:
    """transfer_conversation 应将 status 改为 transferred 并记录 reason。"""
    from app.services.conversation_service import transfer_conversation

    conv = _make_conv(status="active")
    db = AsyncMock()
    db.add = MagicMock()

    scalar_mock = MagicMock()
    scalar_mock.scalar_one_or_none = MagicMock(return_value=conv)
    scalars_mock = MagicMock()
    scalars_mock.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))

    call_count = 0

    async def _execute(stmt: object) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return scalar_mock  # 查 Conversation
        return scalars_mock    # 查 Staff 列表（空）

    db.execute = _execute

    result = await transfer_conversation(db, conv.id, reason="用户投诉", summary="订单问题")

    assert result.status == "transferred"
    assert result.transfer_reason == "用户投诉"
    db.add.assert_called_once_with(conv)
    db.commit.assert_called()


async def test_transfer_conversation_truncates_long_reason() -> None:
    """超过 512 字符的 reason 应被截断。"""
    from app.services.conversation_service import transfer_conversation

    conv = _make_conv(status="active")
    db = AsyncMock()
    db.add = MagicMock()

    scalar_mock = MagicMock()
    scalar_mock.scalar_one_or_none = MagicMock(return_value=conv)
    scalars_mock = MagicMock()
    scalars_mock.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))

    call_count = 0

    async def _execute(stmt: object) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return scalar_mock
        return scalars_mock

    db.execute = _execute

    long_reason = "x" * 600
    result = await transfer_conversation(db, conv.id, reason=long_reason)

    assert len(result.transfer_reason) == 512


async def test_transfer_conversation_not_found_raises() -> None:
    """会话不存在时应抛出 NotFoundError。"""
    from app.core.exceptions import NotFoundError
    from app.services.conversation_service import transfer_conversation

    db = AsyncMock()
    scalar_mock = MagicMock()
    scalar_mock.scalar_one_or_none = MagicMock(return_value=None)
    db.execute = AsyncMock(return_value=scalar_mock)

    with pytest.raises(NotFoundError):
        await transfer_conversation(db, uuid.uuid4(), reason="test")


async def test_transfer_conversation_auto_assigns_staff() -> None:
    """有活跃客服时，transfer_conversation 应自动分配。"""
    from app.services.conversation_service import transfer_conversation

    conv = _make_conv(status="active")
    staff = _make_staff()
    db = AsyncMock()
    db.add = MagicMock()

    # 第1次 execute：查 Conversation → 返回 conv
    # 第2次 execute：查 Staff 列表 → 返回 [staff]
    # 第3次 execute：查该客服当前 transferred 会话数 → 返回 []（0条）
    scalars_with_staff = MagicMock()
    scalars_with_staff.scalars = MagicMock(
        return_value=MagicMock(all=MagicMock(return_value=[staff]))
    )

    empty_scalars = MagicMock()
    empty_scalars.scalars = MagicMock(
        return_value=MagicMock(all=MagicMock(return_value=[]))
    )

    scalar_conv = MagicMock()
    scalar_conv.scalar_one_or_none = MagicMock(return_value=conv)

    call_count = 0

    async def _execute(stmt: object) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return scalar_conv
        if call_count == 2:
            return scalars_with_staff
        return empty_scalars  # 负载查询

    db.execute = _execute

    result = await transfer_conversation(db, conv.id, reason="测试")

    assert result.assigned_staff_id == staff.id


# ── assign_staff ───────────────────────────────────────────────────────────────


async def test_assign_staff_sets_staff_id() -> None:
    """assign_staff 应将 assigned_staff_id 更新为指定客服。"""
    from app.services.conversation_service import assign_staff

    conv = _make_conv()
    staff = _make_staff()
    db = AsyncMock()
    db.add = MagicMock()

    scalar_conv = MagicMock()
    scalar_conv.scalar_one_or_none = MagicMock(return_value=conv)

    scalar_staff = MagicMock()
    scalar_staff.scalar_one_or_none = MagicMock(return_value=staff)

    call_count = 0

    async def _execute(stmt: object) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return scalar_conv
        return scalar_staff

    db.execute = _execute

    result = await assign_staff(db, conv.id, staff_id=staff.id)

    assert result.assigned_staff_id == staff.id
    db.add.assert_called_once_with(conv)
    db.commit.assert_called()


async def test_assign_staff_conversation_not_found_raises() -> None:
    """会话不存在时 assign_staff 应抛出 NotFoundError。"""
    from app.core.exceptions import NotFoundError
    from app.services.conversation_service import assign_staff

    db = AsyncMock()
    scalar_mock = MagicMock()
    scalar_mock.scalar_one_or_none = MagicMock(return_value=None)
    db.execute = AsyncMock(return_value=scalar_mock)

    with pytest.raises(NotFoundError):
        await assign_staff(db, uuid.uuid4(), staff_id=uuid.uuid4())


async def test_assign_staff_inactive_staff_raises() -> None:
    """非活跃/不存在的客服应抛出 NotFoundError。"""
    from app.core.exceptions import NotFoundError
    from app.services.conversation_service import assign_staff

    conv = _make_conv()
    db = AsyncMock()

    scalar_conv = MagicMock()
    scalar_conv.scalar_one_or_none = MagicMock(return_value=conv)

    scalar_none = MagicMock()
    scalar_none.scalar_one_or_none = MagicMock(return_value=None)

    call_count = 0

    async def _execute(stmt: object) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return scalar_conv
        return scalar_none  # staff not found

    db.execute = _execute

    with pytest.raises(NotFoundError):
        await assign_staff(db, conv.id, staff_id=uuid.uuid4())


# ── _auto_assign_staff ─────────────────────────────────────────────────────────


async def test_auto_assign_no_staff_returns_none() -> None:
    """没有活跃客服时，_auto_assign_staff 应返回 None。"""
    from app.services.conversation_service import _auto_assign_staff

    db = AsyncMock()
    scalars_empty = MagicMock()
    scalars_empty.scalars = MagicMock(
        return_value=MagicMock(all=MagicMock(return_value=[]))
    )
    db.execute = AsyncMock(return_value=scalars_empty)

    result = await _auto_assign_staff(db, uuid.uuid4())
    assert result is None


async def test_auto_assign_picks_least_loaded_staff() -> None:
    """_auto_assign_staff 应选择当前 transferred 会话数最少的客服。"""
    from app.services.conversation_service import _auto_assign_staff

    staff_a = _make_staff()
    staff_a.id = uuid.uuid4()
    staff_b = _make_staff()
    staff_b.id = uuid.uuid4()

    # staff_a 有 2 个进行中会话，staff_b 有 0 个
    conv_1 = _make_conv(status="transferred")
    conv_2 = _make_conv(status="transferred")

    db = AsyncMock()
    call_count = 0

    scalars_staff_list = MagicMock()
    scalars_staff_list.scalars = MagicMock(
        return_value=MagicMock(all=MagicMock(return_value=[staff_a, staff_b]))
    )

    scalars_a_convs = MagicMock()
    scalars_a_convs.scalars = MagicMock(
        return_value=MagicMock(all=MagicMock(return_value=[conv_1, conv_2]))
    )

    scalars_b_convs = MagicMock()
    scalars_b_convs.scalars = MagicMock(
        return_value=MagicMock(all=MagicMock(return_value=[]))
    )

    async def _execute(stmt: object) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return scalars_staff_list
        if call_count == 2:
            return scalars_a_convs  # staff_a 的负载
        return scalars_b_convs      # staff_b 的负载

    db.execute = _execute

    result = await _auto_assign_staff(db, uuid.uuid4())

    # 应该选负载最少的 staff_b
    assert result is staff_b
