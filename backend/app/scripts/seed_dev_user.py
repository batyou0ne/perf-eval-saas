import asyncio

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.crud.user import get_user_by_email
from app.models import Company, User, UserRole

SEED_EMAIL = "admin@acmecorp.io"
SEED_PASSWORD = "devpassword123"


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        existing = await get_user_by_email(session, SEED_EMAIL)
        if existing is not None:
            print(f"Seed user already exists: {SEED_EMAIL}")
            return

        company = Company(name="Acme Inc.")
        session.add(company)
        await session.flush()

        admin = User(
            company_id=company.id,
            email=SEED_EMAIL,
            hashed_password=hash_password(SEED_PASSWORD),
            full_name="Ada Admin",
            role=UserRole.COMPANY_ADMIN,
        )
        session.add(admin)
        await session.commit()

        print(f"Created company {company.id} and user {admin.email} / {SEED_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
