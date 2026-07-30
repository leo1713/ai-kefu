from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.security import decode_access_token
from app.websocket.manager import manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/staff")
async def staff_websocket(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
) -> None:
    try:
        payload = decode_access_token(token)
        staff_id = str(payload["sub"])
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await manager.connect(staff_id, websocket)
    try:
        while True:
            # 保持连接活跃；客户端可发心跳 "ping"
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(staff_id, websocket)
