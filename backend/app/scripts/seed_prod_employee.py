import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.crud.user import get_user_by_email
from app.models import Company, User, UserRole

EMPLOYEE_EMAIL = "employee@demo.io"
EMPLOYEE_PASSWORD = "6oOF8zL4Le85uAnM"
EMPLOYEE_FULL_NAME = "Demo Employee"


async def main() -> None:
    async with AsyncSessionLocal() as session:
        existing = await get_user_by_email(session, EMPLOYEE_EMAIL)
        if existing is not None:
            print(f"User already exists: {EMPLOYEE_EMAIL}")
            return

        company = (await session.execute(select(Company).order_by(Company.created_at))).scalars().first()
        if company is None:
            print("No company found — create one first (see seed_prod_admin.py).")
            return

        user = User(
            company_id=company.id,
            email=EMPLOYEE_EMAIL,
            hashed_password=hash_password(EMPLOYEE_PASSWORD),
            full_name=EMPLOYEE_FULL_NAME,
            role=UserRole.EMPLOYEE,
        )
        session.add(user)
        await session.commit()
        print(f"Created employee {user.email} in company {company.id}")


if __name__ == "__main__":
    asyncio.run(main())
