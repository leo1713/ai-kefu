from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.admin import ApiKeySaveRequest, SettingsResponse
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/settings/api-key")
async def save_api_key(
    data: ApiKeySaveRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    await admin_service.save_api_key(db, "anthropic_api_key", data.api_key)
    return {"status": "saved"}


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)) -> SettingsResponse:
    key = await admin_service.get_api_key(db, "anthropic_api_key")
    return SettingsResponse(
        anthropic_api_key=admin_service.mask_key(key) if key else None
    )
