from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas.analytics import AnalyticsOverview
from app.services import analytics_service

router = APIRouter()


@router.get("/analytics/overview", response_model=AnalyticsOverview)
async def get_analytics_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COMPANY_ADMIN, UserRole.HR)),
) -> AnalyticsOverview:
    return await analytics_service.get_overview(db, current_user)
