from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import wecom_service

router = APIRouter(prefix="/wecom", tags=["wecom-internal"])


@router.get("/callback")
async def verify_url(
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...),
) -> Response:
    crypto = wecom_service.get_crypto()
    if not crypto.verify_signature(msg_signature, timestamp, nonce, echostr):
        return Response(status_code=403)
    plaintext = crypto.decrypt(echostr)
    return Response(content=plaintext, media_type="text/plain")


@router.post("/callback")
async def receive_message(
    request: Request,
    background_tasks: BackgroundTasks,
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> Response:
    body = await request.body()
    xml_str = body.decode("utf-8")

    from xml.etree import ElementTree as ET
    root = ET.fromstring(xml_str)
    encrypt_elem = root.find("Encrypt")
    if encrypt_elem is None or not encrypt_elem.text:
        return Response(content="success", media_type="text/plain")

    crypto = wecom_service.get_crypto()
    if not crypto.verify_signature(msg_signature, timestamp, nonce, encrypt_elem.text):
        return Response(status_code=403)

    plaintext = crypto.decrypt(encrypt_elem.text)
    background_tasks.add_task(wecom_service.handle_message, db, plaintext)
    return Response(content="success", media_type="text/plain")
