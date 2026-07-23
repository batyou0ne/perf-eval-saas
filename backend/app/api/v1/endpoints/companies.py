from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.core.database import get_db
from app.models.user import UserRole
from app.schemas.company import CompanyCreate, CompanyRead
from app.services import company_service

router = APIRouter()


@router.post("/companies", response_model=CompanyRead, dependencies=[Depends(require_role(UserRole.SUPER_ADMIN))])
async def create_company(body: CompanyCreate, db: AsyncSession = Depends(get_db)) -> CompanyRead:
    return await company_service.create_company(db, body)


@router.get(
    "/companies", response_model=list[CompanyRead], dependencies=[Depends(require_role(UserRole.SUPER_ADMIN))]
)
async def list_companies(db: AsyncSession = Depends(get_db)) -> list[CompanyRead]:
    return await company_service.get_companies(db)
