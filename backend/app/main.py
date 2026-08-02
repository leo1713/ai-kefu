from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.internal.wecom import router as wecom_internal_router
from app.api.v1.admin import router as admin_router
from app.api.v1.agents import router as agents_router
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.qa import router as qa_router
from app.api.v1.staff import router as staff_router
from app.api.v1.stats import router as stats_router
from app.api.v1.visitors import router as visitors_router
from app.api.v1.workflows import router as workflows_router
from app.api.v1.ws import router as ws_router
from app.config import settings
from app.core.exceptions import AppException
from app.core.logging import configure_logging, logger
from app.core.middleware import RequestLoggingMiddleware

_INSECURE_SECRET_KEY = "changeme-in-production"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging(debug=settings.debug)
    # S-05: 非 debug 模式下拒绝使用默认 secret_key，避免签名伪造
    if not settings.debug and settings.secret_key == _INSECURE_SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY 使用了默认值，生产环境禁止启动。"
            " 请在 .env 中设置随机强密钥。"
            " 生成命令：python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    logger.info("startup", app=settings.app_name)
    yield
    logger.info("shutdown")


app = FastAPI(
    title="AI Customer Service API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url=None,
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.error_code, "message": exc.message, "details": {}}},
    )


@app.get("/health")
async def health() -> JSONResponse:
    """
    健康检查。检查 DB 和 Redis 连通性，全部正常返回 200，任意失败返回 503。
    """
    from sqlalchemy import text

    from app.database import engine

    checks: dict[str, str] = {}

    # DB ping
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as e:
        logger.warning("health_db_failed", error=str(e))
        checks["db"] = f"error: {e}"

    # Redis ping
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()  # type: ignore[attr-defined]
        checks["redis"] = "ok"
    except Exception as e:
        logger.warning("health_redis_failed", error=str(e))
        checks["redis"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ok" if all_ok else "degraded", **checks},
    )


app.include_router(auth_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(agents_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(conversations_router, prefix="/api/v1")
app.include_router(knowledge_router, prefix="/api/v1")
app.include_router(qa_router, prefix="/api/v1")
app.include_router(staff_router, prefix="/api/v1")
app.include_router(stats_router, prefix="/api/v1")
app.include_router(visitors_router, prefix="/api/v1")
app.include_router(workflows_router, prefix="/api/v1")
app.include_router(wecom_internal_router, prefix="/api/internal")
app.include_router(ws_router)
