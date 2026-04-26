from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.supabase import get_supabase
from app.schemas.households import HouseholdCreate, HouseholdMemberLink, HouseholdOut


class HouseholdService:
    def __init__(self) -> None:
        self.sb = get_supabase()

    def create_household(self, payload: HouseholdCreate) -> HouseholdOut:
        household_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        self.sb.table("households").insert(
            {
                "id": household_id,
                "gps_lat": payload.gps_lat,
                "gps_long": payload.gps_long,
                "address_desc": payload.address_desc,
                "household_size": payload.household_size,
                "created_at": created_at,
            }
        ).execute()

        return self.get_household(household_id) or HouseholdOut(
            id=household_id,
            gps_lat=payload.gps_lat,
            gps_long=payload.gps_long,
            address_desc=payload.address_desc,
            household_size=payload.household_size,
            created_at=datetime.fromisoformat(created_at.replace("Z", "+00:00")),
            members=[],
        )

    def get_household(self, household_id: str) -> Optional[HouseholdOut]:
        hh = (
            self.sb.table("households")
            .select("id,gps_lat,gps_long,address_desc,household_size,created_at")
            .eq("id", household_id)
            .maybe_single()
            .execute()
        )
        if not hh.data:
            return None

        members = (
            self.sb.table("household_members")
            .select("id,patient_id,relationship,is_index_case")
            .eq("household_id", household_id)
            .execute()
        )

        return HouseholdOut(
            id=hh.data.get("id"),
            gps_lat=hh.data.get("gps_lat"),
            gps_long=hh.data.get("gps_long"),
            address_desc=hh.data.get("address_desc"),
            household_size=hh.data.get("household_size"),
            created_at=_parse_dt(hh.data.get("created_at")),
            members=members.data or [],
        )

    def link_member(self, household_id: str, payload: HouseholdMemberLink) -> dict[str, Any]:
        hh = self.get_household(household_id)
        if not hh:
            raise ValueError("Household not found")

        member_id = str(uuid.uuid4())
        self.sb.table("household_members").insert(
            {
                "id": member_id,
                "household_id": household_id,
                "patient_id": payload.patient_id,
                "relationship": payload.relationship,
                "is_index_case": payload.is_index_case,
            }
        ).execute()

        return {"id": member_id, "household_id": household_id, "patient_id": payload.patient_id}


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

