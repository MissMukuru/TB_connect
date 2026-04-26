from fastapi import APIRouter

from app.api.routers import consent, households, intake, patients, risk

api_router = APIRouter()

api_router.include_router(patients.router, prefix="/patients", tags=["patients"])
api_router.include_router(intake.router, prefix="/intake", tags=["intake"])
api_router.include_router(risk.router, prefix="/risk", tags=["risk"])
api_router.include_router(consent.router, prefix="/consent", tags=["consent"])
api_router.include_router(households.router, prefix="/households", tags=["households"])

