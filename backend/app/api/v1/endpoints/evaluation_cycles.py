import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.core.database import get_db
from app.crud.evaluation_cycle import get_cycle_by_id, list_cycles_by_company
from app.models.evaluation_cycle import EvaluationCycle
from app.models.user import User, UserRole
from app.schemas.evaluation_cycle import CycleCreate, CycleDetail, CycleProgress, CycleRead, CycleUpdate
from app.schemas.pagination import Page
from app.services import cycle_service

router = APIRouter()


async def _get_owned_cycle(db: AsyncSession, cycle_id: uuid.UUID, current_user: User) -> EvaluationCycle:
    cycle = await get_cycle_by_id(db, cycle_id)
    if cycle is None or cycle.company_id != current_user.company_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cycle not found")
    return cycle


@router.post("/cycles", response_model=CycleDetail)
async def create_cycle(
    body: CycleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COMPANY_ADMIN, UserRole.HR)),
) -> CycleDetail:
    return await cycle_service.create_cycle(db, current_user.company_id, body)


@router.get("/cycles", response_model=Page[CycleRead])
async def list_cycles(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COMPANY_ADMIN, UserRole.HR)),
) -> Page[CycleRead]:
    cycles, total = await list_cycles_by_company(
        db, current_user.company_id, offset=(page - 1) * page_size, limit=page_size
    )
    return Page(
        items=[CycleRead.model_validate(c) for c in cycles], total=total, page=page, page_size=page_size
    )


@router.get("/cycles/{cycle_id}", response_model=CycleDetail)
async def get_cycle(
    cycle_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COMPANY_ADMIN, UserRole.HR)),
) -> CycleDetail:
    return await _get_owned_cycle(db, cycle_id, current_user)


@router.patch("/cycles/{cycle_id}", response_model=CycleDetail)
async def update_cycle(
    cycle_id: uuid.UUID,
    body: CycleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COMPANY_ADMIN, UserRole.HR)),
) -> CycleDetail:
    cycle = await _get_owned_cycle(db, cycle_id, current_user)
    return await cycle_service.update_cycle(db, cycle, body)


@router.post("/cycles/{cycle_id}/activate", response_model=CycleRead)
async def activate_cycle(
    cycle_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COMPANY_ADMIN, UserRole.HR)),
) -> CycleRead:
    cycle = await _get_owned_cycle(db, cycle_id, current_user)
    return await cycle_service.activate_cycle(db, cycle)


@router.post("/cycles/{cycle_id}/close", response_model=CycleRead)
async def close_cycle(
    cycle_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COMPANY_ADMIN, UserRole.HR)),
) -> CycleRead:
    cycle = await _get_owned_cycle(db, cycle_id, current_user)
    return await cycle_service.close_cycle(db, cycle)


@router.get("/cycles/{cycle_id}/progress", response_model=CycleProgress)
async def get_cycle_progress(
    cycle_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COMPANY_ADMIN, UserRole.HR)),
) -> CycleProgress:
    cycle = await _get_owned_cycle(db, cycle_id, current_user)
    return await cycle_service.get_cycle_progress(db, cycle)
