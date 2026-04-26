from fastapi import APIRouter

from app.schemas.risk import RiskScoreRequest, RiskScoreResponse
from app.services.risk_service import RiskService

router = APIRouter()


@router.post("/score", response_model=RiskScoreResponse)
def score(payload: RiskScoreRequest) -> RiskScoreResponse:
    return RiskService().score(payload)

