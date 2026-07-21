from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import AsyncSessionLocal
from app.core.redis import redis_client

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    status = {"api": "ok", "database": "unreachable", "redis": "unreachable"}

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        status["database"] = "ok"
    except Exception:
        pass

    try:
        await redis_client.ping()
        status["redis"] = "ok"
    except Exception:
        pass

    return status
