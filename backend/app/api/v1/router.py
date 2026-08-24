from fastapi import APIRouter

from app.api.v1.endpoints import (
    analytics,
    auth,
    companies,
    evaluation_cycles,
    evaluation_summaries,
    evaluations,
    health,
    invites,
    tasks,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(invites.router, tags=["invites"])
api_router.include_router(companies.router, tags=["companies"])
api_router.include_router(users.router, tags=["users"])
api_router.include_router(evaluation_cycles.router, tags=["evaluation-cycles"])
api_router.include_router(evaluations.router, tags=["evaluations"])
api_router.include_router(evaluation_summaries.router, tags=["evaluation-summaries"])
api_router.include_router(tasks.router, tags=["tasks"])
api_router.include_router(analytics.router, tags=["analytics"])
