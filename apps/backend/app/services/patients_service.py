from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.supabase import get_supabase
from app.schemas.patients import PatientCreate, PatientOut, PatientUpdate


class PatientsService:
    def __init__(self) -> None:
        self.sb = get_supabase()

    def create_patient(self, payload: PatientCreate) -> PatientOut:
        email = payload.email or f"patient.{uuid.uuid4().hex[:8]}@shieldtb.ke"
        password = self._gen_password()

        auth_res = self.sb.auth.admin.create_user(
            {
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {"full_name": payload.full_name, "role": "patient"},
            }
        )
        if not auth_res or not getattr(auth_res, "user", None):
            raise ValueError("Failed to create auth user")

        patient_id = auth_res.user.id
        created_at = datetime.now(timezone.utc).isoformat()

        self.sb.table("profiles").insert(
            {
                "id": patient_id,
                "full_name": payload.full_name,
                "role": "patient",
                "facility_id": payload.facility_id,
                "created_at": created_at,
            }
        ).execute()

        self.sb.table("patients").insert(
            {
                "id": patient_id,
                "phone": payload.phone,
                "created_at": created_at,
            }
        ).execute()

        return self.get_patient(patient_id) or PatientOut(
            id=patient_id,
            phone=payload.phone,
            created_at=datetime.fromisoformat(created_at.replace("Z", "+00:00")),
            profile={"full_name": payload.full_name, "role": "patient", "facility_id": payload.facility_id},
        )

    def get_patient(self, patient_id: str) -> Optional[PatientOut]:
        p = self.sb.table("patients").select("id,phone,created_at").eq("id", patient_id).maybe_single().execute()
        if not p.data:
            return None

        prof = (
            self.sb.table("profiles")
            .select("id,full_name,role,facility_id,created_at")
            .eq("id", patient_id)
            .maybe_single()
            .execute()
        )

        return PatientOut(
            id=p.data.get("id"),
            phone=p.data.get("phone"),
            created_at=_parse_dt(p.data.get("created_at")),
            profile=prof.data or {},
        )

    def list_patients(self, limit: int, offset: int) -> list[PatientOut]:
        res = (
            self.sb.table("patients")
            .select("id,phone,created_at")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        rows = res.data or []
        out: list[PatientOut] = []
        for r in rows:
            out.append(
                PatientOut(
                    id=r.get("id"),
                    phone=r.get("phone"),
                    created_at=_parse_dt(r.get("created_at")),
                    profile={},
                )
            )
        return out

    def update_patient(self, patient_id: str, payload: PatientUpdate) -> Optional[PatientOut]:
        existing = self.get_patient(patient_id)
        if not existing:
            return None

        patient_updates: dict[str, Any] = {}
        if payload.phone is not None:
            patient_updates["phone"] = payload.phone
        if patient_updates:
            self.sb.table("patients").update(patient_updates).eq("id", patient_id).execute()

        profile_updates: dict[str, Any] = {}
        if payload.full_name is not None:
            profile_updates["full_name"] = payload.full_name
        if payload.facility_id is not None:
            profile_updates["facility_id"] = payload.facility_id
        if profile_updates:
            self.sb.table("profiles").update(profile_updates).eq("id", patient_id).execute()

        return self.get_patient(patient_id)

    def delete_patient(self, patient_id: str) -> bool:
        existing = self.get_patient(patient_id)
        if not existing:
            return False

        # Delete application rows first; Auth deletion is optional and may be restricted.
        self.sb.table("patients").delete().eq("id", patient_id).execute()
        self.sb.table("profiles").delete().eq("id", patient_id).execute()
        return True

    def _gen_password(self) -> str:
        # Strong enough for server-side created accounts. Not returned by API.
        return "ShieldTB@" + secrets.token_urlsafe(12)


def _parse_dt(val: Any) -> Optional[datetime]:
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        s = str(val)
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None

