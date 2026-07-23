import asyncio

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.crud.user import get_user_by_email
from app.models import Company, User, UserRole

COMPANY_ADMIN_EMAIL = "admin@acmecorp.io"
COMPANY_ADMIN_PASSWORD = "devpassword123"

SUPER_ADMIN_EMAIL = "superadmin@platform.io"
SUPER_ADMIN_PASSWORD = "devpassword123"


async def seed_company_admin(session) -> None:
    existing = await get_user_by_email(session, COMPANY_ADMIN_EMAIL)
    if existing is not None:
        print(f"Seed user already exists: {COMPANY_ADMIN_EMAIL}")
        return

    company = Company(name="Acme Inc.")
    session.add(company)
    await session.flush()

    admin = User(
        company_id=company.id,
        email=COMPANY_ADMIN_EMAIL,
        hashed_password=hash_password(COMPANY_ADMIN_PASSWORD),
        full_name="Ada Admin",
        role=UserRole.COMPANY_ADMIN,
    )
    session.add(admin)
    await session.commit()

    print(f"Created company {company.id} and user {admin.email} / {COMPANY_ADMIN_PASSWORD}")


async def seed_super_admin(session) -> None:
    existing = await get_user_by_email(session, SUPER_ADMIN_EMAIL)
    if existing is not None:
        print(f"Seed user already exists: {SUPER_ADMIN_EMAIL}")
        return

    super_admin = User(
        company_id=None,
        email=SUPER_ADMIN_EMAIL,
        hashed_password=hash_password(SUPER_ADMIN_PASSWORD),
        full_name="Sam Super",
        role=UserRole.SUPER_ADMIN,
    )
    session.add(super_admin)
    await session.commit()

    print(f"Created user {super_admin.email} / {SUPER_ADMIN_PASSWORD}")


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        await seed_company_admin(session)
        await seed_super_admin(session)


if __name__ == "__main__":
    asyncio.run(seed())
