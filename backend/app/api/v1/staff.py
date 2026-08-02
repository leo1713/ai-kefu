import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.staff import Staff
from app.schemas.staff import StaffCreate, StaffResponse, StaffUpdate
from app.services import staff_service

router = APIRouter(prefix="/staff", tags=["staff"])


@router.get("", response_model=list[StaffResponse])
async def get_staff_list(
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(get_current_user),
) -> list[StaffResponse]:
    staff = await staff_service.list_staff(db, include_inactive=include_inactive)
    return [StaffResponse.model_validate(s) for s in staff]


@router.post("", response_model=StaffResponse, status_code=201)
async def post_staff(
    data: StaffCreate,
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(get_current_user),
) -> StaffResponse:
    staff = await staff_service.create_staff(db, data)
    return StaffResponse.model_validate(staff)


@router.get("/{staff_id}", response_model=StaffResponse)
async def get_staff_by_id(
    staff_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(get_current_user),
) -> StaffResponse:
    staff = await staff_service.get_staff(db, staff_id)
    return StaffResponse.model_validate(staff)


@router.patch("/{staff_id}", response_model=StaffResponse)
async def patch_staff(
    staff_id: uuid.UUID,
    data: StaffUpdate,
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(get_current_user),
) -> StaffResponse:
    staff = await staff_service.update_staff(db, staff_id, data)
    return StaffResponse.model_validate(staff)
