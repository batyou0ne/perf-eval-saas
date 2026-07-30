import asyncio
import getpass

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.crud.user import get_user_by_email
from app.models import Company, User, UserRole


async def main() -> None:
    email = input("Company admin email: ").strip()
    password = getpass.getpass("Password (not echoed): ")
    company_name = input("Company name: ").strip()

    async with AsyncSessionLocal() as session:
        existing = await get_user_by_email(session, email)
        if existing is not None:
            print(f"User already exists: {email}")
            return

        company = Company(name=company_name)
        session.add(company)
        await session.flush()

        admin = User(
            company_id=company.id,
            email=email,
            hashed_password=hash_password(password),
            full_name="Admin",
            role=UserRole.COMPANY_ADMIN,
        )
        session.add(admin)
        await session.commit()
        print(f"Created company {company.id} and user {admin.email}")


if __name__ == "__main__":
    asyncio.run(main())
