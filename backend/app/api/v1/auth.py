import uuid

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database import get_db
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.staff import StaffResponse
from app.services import auth_service, staff_service

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer()


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    token = await auth_service.login(db, data.username, data.password)
    return TokenResponse(access_token=token)


@router.post("/init-admin", status_code=201)
async def init_admin(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    staff = await auth_service.seed_default_admin(db)
    return {"username": staff.username, "display_name": staff.display_name}


@router.get("/me", response_model=StaffResponse)
async def get_me(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> StaffResponse:
    payload = decode_access_token(creds.credentials)
    staff_id = uuid.UUID(str(payload["sub"]))
    staff = await staff_service.get_staff(db, staff_id)
    return StaffResponse.model_validate(staff)
