from __future__ import annotations

import httpx
import structlog

logger = structlog.get_logger()


class WeComClient:
    _BASE = "https://qyapi.weixin.qq.com/cgi-bin"

    def __init__(self, corp_id: str, secret: str) -> None:
        self._corp_id = corp_id
        self._secret = secret
        self._token: str = ""

    async def _get_token(self) -> str:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{self._BASE}/gettoken",
                params={"corpid": self._corp_id, "corpsecret": self._secret},
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("errcode", 0) != 0:
                raise RuntimeError(f"WeCom token error: {data}")
            self._token = data["access_token"]
            return self._token

    async def send_text(self, to_user: str, agent_id: str, content: str) -> None:
        token = await self._get_token()
        payload = {
            "touser": to_user,
            "msgtype": "text",
            "agentid": agent_id,
            "text": {"content": content},
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self._BASE}/message/send",
                params={"access_token": token},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("errcode", 0) != 0:
                logger.warning("wecom_send_failed", errcode=data.get("errcode"), errmsg=data.get("errmsg"))
