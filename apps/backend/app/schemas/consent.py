from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ConsentGrantRequest(BaseModel):
    consent_type: str = Field(min_length=2, max_length=50)
    version: Optional[str] = Field(default=None, max_length=50)
    method: Optional[str] = Field(default=None, max_length=50)
    captured_by: Optional[str] = None
    captured_at: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConsentRevokeRequest(BaseModel):
    consent_type: str = Field(min_length=2, max_length=50)
    reason: Optional[str] = Field(default=None, max_length=250)
    captured_by: Optional[str] = None
    captured_at: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConsentOut(BaseModel):
    id: str
    patient_id: str
    consent_type: str
    status: str
    version: Optional[str] = None
    method: Optional[str] = None
    captured_by: Optional[str] = None
    captured_at: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

