from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class HouseholdCreate(BaseModel):
    gps_lat: float
    gps_long: float
    address_desc: str = Field(min_length=2, max_length=500)
    household_size: Optional[int] = Field(default=None, ge=1, le=50)


class HouseholdMemberLink(BaseModel):
    patient_id: str
    relationship: str = Field(default="other", max_length=50)
    is_index_case: bool = False


class HouseholdOut(BaseModel):
    id: str
    gps_lat: Optional[float] = None
    gps_long: Optional[float] = None
    address_desc: Optional[str] = None
    household_size: Optional[int] = None
    created_at: Optional[datetime] = None

    members: list[dict[str, Any]] = Field(default_factory=list)

