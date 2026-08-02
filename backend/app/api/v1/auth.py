from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.staff import Staff
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.staff import StaffResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    token = await auth_service.login(db, data.username, data.password)
    return TokenResponse(access_token=token)


@router.post("/init-admin", status_code=201)
async def init_admin(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """
    初始化默认管理员账号。受 ALLOW_INIT_ADMIN 和 DEFAULT_ADMIN_PASSWORD 环境变量控制。
    首次使用后应将 ALLOW_INIT_ADMIN 改回 false 并重启服务。
    """
    staff = await auth_service.seed_default_admin(db)
    return {"username": staff.username, "display_name": staff.display_name}


@router.get("/me", response_model=StaffResponse)
async def get_me(current_user: Staff = Depends(get_current_user)) -> StaffResponse:
    return StaffResponse.model_validate(current_user)
