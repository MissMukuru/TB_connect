from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


class PatientCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    phone: str = Field(min_length=7, max_length=30)
    facility_id: Optional[str] = None
    email: Optional[EmailStr] = None


class PatientUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    phone: Optional[str] = Field(default=None, min_length=7, max_length=30)
    facility_id: Optional[str] = None


class PatientOut(BaseModel):
    id: str
    phone: Optional[str] = None
    created_at: Optional[datetime] = None

    profile: dict[str, Any] = Field(default_factory=dict)

