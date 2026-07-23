from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.company import list_companies
from app.models.company import Company
from app.schemas.company import CompanyCreate


async def create_company(db: AsyncSession, data: CompanyCreate) -> Company:
    company = Company(name=data.name)
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return company


async def get_companies(db: AsyncSession) -> list[Company]:
    return await list_companies(db)
