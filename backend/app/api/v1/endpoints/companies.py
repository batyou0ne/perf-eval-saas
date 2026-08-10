from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.core.database import get_db
from app.models.user import UserRole
from app.schemas.company import CompanyCreate, CompanyOption, CompanyRead
from app.schemas.pagination import Page
from app.services import company_service

router = APIRouter()


@router.post("/companies", response_model=CompanyRead, dependencies=[Depends(require_role(UserRole.SUPER_ADMIN))])
async def create_company(body: CompanyCreate, db: AsyncSession = Depends(get_db)) -> CompanyRead:
    return await company_service.create_company(db, body)


# Declared before any parameterised /companies/... route so the literal path wins.
@router.get(
    "/companies/options",
    response_model=list[CompanyOption],
    dependencies=[Depends(require_role(UserRole.SUPER_ADMIN))],
)
async def list_company_options(db: AsyncSession = Depends(get_db)) -> list[CompanyOption]:
    """Every company, unpaginated — this feeds the invite form's company picker."""
    return await company_service.get_company_options(db)


@router.get(
    "/companies", response_model=Page[CompanyRead], dependencies=[Depends(require_role(UserRole.SUPER_ADMIN))]
)
async def list_companies(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> Page[CompanyRead]:
    return await company_service.get_companies(db, page, page_size)
