from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.company import list_all_companies, list_companies
from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyRead
from app.schemas.pagination import Page


async def create_company(db: AsyncSession, data: CompanyCreate) -> Company:
    company = Company(name=data.name)
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return company


async def get_companies(db: AsyncSession, page: int, page_size: int) -> Page[CompanyRead]:
    companies, total = await list_companies(db, offset=(page - 1) * page_size, limit=page_size)
    return Page(
        items=[CompanyRead.model_validate(c) for c in companies], total=total, page=page, page_size=page_size
    )


async def get_company_options(db: AsyncSession) -> list[Company]:
    return await list_all_companies(db)
