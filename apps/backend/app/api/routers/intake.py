from fastapi import APIRouter, Depends, HTTPException

from app.schemas.intake import IntakeRequest, IntakeResponse
from app.services.intake_service import IntakeService

router = APIRouter()


def _svc() -> IntakeService:
    return IntakeService()


@router.post("", response_model=IntakeResponse, status_code=201)
def intake(payload: IntakeRequest, svc: IntakeService = Depends(_svc)) -> IntakeResponse:
    try:
        return svc.run_intake(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

