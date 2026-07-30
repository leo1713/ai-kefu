from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket

import structlog

logger = structlog.get_logger()


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, staff_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(staff_id, set()).add(websocket)
        logger.info("ws_connected", staff_id=staff_id)

    def disconnect(self, staff_id: str, websocket: WebSocket) -> None:
        conns = self._connections.get(staff_id, set())
        conns.discard(websocket)
        if not conns:
            self._connections.pop(staff_id, None)
        logger.info("ws_disconnected", staff_id=staff_id)

    async def send_to_staff(self, staff_id: str, data: dict[str, Any]) -> None:
        conns = list(self._connections.get(staff_id, set()))
        if not conns:
            return
        payload = json.dumps(data, ensure_ascii=False, default=str)
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.get(staff_id, set()).discard(ws)


manager = ConnectionManager()
