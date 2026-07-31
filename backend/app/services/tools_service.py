from __future__ import annotations

import json
from typing import Any

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()


async def execute_tool(tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    if tool_name == "query_order":
        return await _query_order(tool_input.get("order_id", ""))
    if tool_name == "query_payment":
        return await _query_payment(tool_input.get("order_id", ""))
    if tool_name == "query_logistics":
        return await _query_logistics(
            order_id=tool_input.get("order_id"),
            tracking_no=tool_input.get("tracking_no"),
        )
    return {"error": f"未知工具: {tool_name}"}


async def _query_order(order_id: str) -> dict[str, Any]:
    if settings.order_api_url:
        return await _http_get(f"{settings.order_api_url}/orders/{order_id}")
    return _mock_order(order_id)


async def _query_payment(order_id: str) -> dict[str, Any]:
    if settings.payment_api_url:
        return await _http_get(
            f"{settings.payment_api_url}/payments", params={"order_id": order_id}
        )
    return _mock_payment(order_id)


async def _query_logistics(
    order_id: str | None, tracking_no: str | None
) -> dict[str, Any]:
    key = order_id or tracking_no or ""
    if settings.logistics_api_url:
        return await _http_get(f"{settings.logistics_api_url}/logistics/{key}")
    return _mock_logistics(key)


async def _http_get(
    url: str, params: dict[str, str] | None = None
) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            return r.json()  # type: ignore[no-any-return]
    except Exception as e:
        logger.warning("tool_http_error", url=url, error=str(e))
        return {"error": str(e)}


def _mock_order(order_id: str) -> dict[str, Any]:
    return {
        "order_id": order_id,
        "status": "已发货",
        "created_at": "2026-07-28 10:30:00",
        "total": "299.00",
        "items": [{"name": "示例商品A", "qty": 1, "price": "299.00"}],
        "_note": "模拟数据，配置 ORDER_API_URL 接入真实系统",
    }


def _mock_payment(order_id: str) -> dict[str, Any]:
    return {
        "order_id": order_id,
        "payment_status": "已支付",
        "amount": "299.00",
        "paid_at": "2026-07-28 10:35:00",
        "method": "微信支付",
        "_note": "模拟数据，配置 PAYMENT_API_URL 接入真实系统",
    }


def _mock_logistics(key: str) -> dict[str, Any]:
    return {
        "ref": key,
        "tracking_no": "SF1234567890",
        "carrier": "顺丰速运",
        "status": "派送中",
        "estimated_delivery": "2026-07-31",
        "events": [
            {"time": "2026-07-30 18:00", "desc": "快件已到达【上海转运中心】"},
            {"time": "2026-07-31 08:00", "desc": "快件正在派送，请注意查收"},
        ],
        "_note": "模拟数据，配置 LOGISTICS_API_URL 接入真实系统",
    }
