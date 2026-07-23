from fastapi import APIRouter

from app.api.v1.endpoints import auth, companies, health, invites

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(invites.router, tags=["invites"])
api_router.include_router(companies.router, tags=["companies"])
