from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


class IntakeCondition(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    status: str = "active"


class IntakeSymptom(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    severity: int = Field(default=3, ge=1, le=5)
    duration_days: int = Field(default=14, ge=0, le=3650)


class IntakeHousehold(BaseModel):
    household_id: Optional[str] = None
    gps_lat: Optional[float] = None
    gps_long: Optional[float] = None
    address_desc: Optional[str] = None
    household_size: Optional[int] = Field(default=None, ge=1, le=50)

    relationship: str = Field(default="other", max_length=50)
    is_index_case: bool = False


class IntakePatient(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    phone: str = Field(min_length=7, max_length=30)
    facility_id: Optional[str] = None
    email: Optional[EmailStr] = None


class IntakeRequest(BaseModel):
    patient: IntakePatient
    household: IntakeHousehold
    conditions: list[IntakeCondition] = Field(default_factory=list)
    symptoms: list[IntakeSymptom] = Field(default_factory=list)
    household_contact: bool = False
    cd4: Optional[int] = Field(default=None, ge=0, le=5000)


class IntakeResponse(BaseModel):
    patient_id: str
    household_id: str
    risk: dict[str, Any]
    created_at: datetime

