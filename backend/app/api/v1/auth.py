from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.auth import LoginRequest, TokenResponse
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
    """Dev-only: seed default admin (admin/admin123)."""
    staff = await auth_service.seed_default_admin(db)
    return {"username": staff.username, "display_name": staff.display_name}
