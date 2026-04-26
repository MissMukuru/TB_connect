from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RiskScoreRequest(BaseModel):
    conditions: list[str] = Field(default_factory=list)
    symptoms: list[str] = Field(default_factory=list)
    household_contact: bool = False
    cd4: Optional[int] = Field(default=None, ge=0, le=5000)


class ContributingFactor(BaseModel):
    factor: str
    points: int


class RiskScoreResponse(BaseModel):
    score: int
    score_normalized: float
    risk_level: str
    contributing_factors: list[ContributingFactor]

