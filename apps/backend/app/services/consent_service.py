from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.supabase import get_supabase
from app.schemas.consent import ConsentGrantRequest, ConsentOut, ConsentRevokeRequest


class ConsentService:
    """
    Assumes a `consents` table exists in Supabase.

    Expected columns (recommended):
    - id (uuid pk)
    - patient_id (uuid)
    - consent_type (text)
    - status (text)  # granted|revoked
    - version (text, nullable)
    - method (text, nullable)
    - captured_by (uuid, nullable)
    - captured_at (timestamptz)
    - metadata (jsonb, nullable)
    """

    def __init__(self) -> None:
        self.sb = get_supabase()

    def grant(self, patient_id: str, payload: ConsentGrantRequest) -> ConsentOut:
        consent_id = str(uuid.uuid4())
        captured_at = (payload.captured_at or datetime.now(timezone.utc)).isoformat()

        row = {
            "id": consent_id,
            "patient_id": patient_id,
            "consent_type": payload.consent_type,
            "status": "granted",
            "version": payload.version,
            "method": payload.method,
            "captured_by": payload.captured_by,
            "captured_at": captured_at,
            "metadata": payload.metadata or {},
        }

        self.sb.table("consents").insert(row).execute()
        return self._to_out(row)

    def revoke(self, patient_id: str, payload: ConsentRevokeRequest) -> ConsentOut | None:
        # Record revocation as a new consent event (append-only).
        consent_id = str(uuid.uuid4())
        captured_at = (payload.captured_at or datetime.now(timezone.utc)).isoformat()

        row = {
            "id": consent_id,
            "patient_id": patient_id,
            "consent_type": payload.consent_type,
            "status": "revoked",
            "version": None,
            "method": None,
            "captured_by": payload.captured_by,
            "captured_at": captured_at,
            "metadata": {"reason": payload.reason, **(payload.metadata or {})},
        }
        self.sb.table("consents").insert(row).execute()
        return self._to_out(row)

    def list_for_patient(self, patient_id: str) -> list[ConsentOut]:
        res = (
            self.sb.table("consents")
            .select("id,patient_id,consent_type,status,version,method,captured_by,captured_at,metadata")
            .eq("patient_id", patient_id)
            .order("captured_at", desc=True)
            .execute()
        )
        rows = res.data or []
        return [self._to_out(r) for r in rows]

    def _to_out(self, r: dict[str, Any]) -> ConsentOut:
        return ConsentOut(
            id=r.get("id"),
            patient_id=r.get("patient_id"),
            consent_type=r.get("consent_type"),
            status=r.get("status"),
            version=r.get("version"),
            method=r.get("method"),
            captured_by=r.get("captured_by"),
            captured_at=_parse_dt(r.get("captured_at")),
            metadata=r.get("metadata") or {},
        )


def _parse_dt(val: Any):
    if not val:
        return None
    try:
        s = str(val)
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None

