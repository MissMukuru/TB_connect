from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.supabase import get_supabase
from app.schemas.intake import IntakeRequest, IntakeResponse
from app.schemas.patients import PatientCreate
from app.schemas.risk import RiskScoreRequest
from app.services.patients_service import PatientsService
from app.services.risk_service import RiskService


class IntakeService:
    def __init__(self) -> None:
        self.sb = get_supabase()
        self.patients = PatientsService()
        self.risk = RiskService()

    def run_intake(self, payload: IntakeRequest) -> IntakeResponse:
        created_at = datetime.now(timezone.utc)

        patient = self.patients.create_patient(PatientCreate(**payload.patient.model_dump()))
        patient_id = patient.id

        household_id = self._ensure_household(payload)
        self._link_household_member(household_id, payload, patient_id)

        condition_ids = self._resolve_lookup_ids(
            table="conditions",
            items=[c.model_dump() for c in payload.conditions],
        )
        symptom_ids = self._resolve_lookup_ids(
            table="symptoms",
            items=[s.model_dump() for s in payload.symptoms],
        )

        self._insert_patient_conditions(patient_id, condition_ids, created_at)
        self._insert_patient_symptoms(patient_id, symptom_ids, payload, created_at)

        risk_resp = self.risk.score(
            RiskScoreRequest(
                conditions=[c for c in condition_ids["names"]],
                symptoms=[s for s in symptom_ids["names"]],
                household_contact=payload.household_contact,
                cd4=payload.cd4,
            )
        )

        self._save_risk_score(patient_id, risk_resp, created_at)

        return IntakeResponse(
            patient_id=patient_id,
            household_id=household_id,
            risk=risk_resp.model_dump(),
            created_at=created_at,
        )

    def _ensure_household(self, payload: IntakeRequest) -> str:
        hh = payload.household
        if hh.household_id:
            return hh.household_id

        if hh.gps_lat is None or hh.gps_long is None or not hh.address_desc:
            raise ValueError("Either household_id or (gps_lat, gps_long, address_desc) is required")

        household_id = str(uuid.uuid4())
        self.sb.table("households").insert(
            {
                "id": household_id,
                "gps_lat": hh.gps_lat,
                "gps_long": hh.gps_long,
                "address_desc": hh.address_desc,
                "household_size": hh.household_size,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()
        return household_id

    def _link_household_member(self, household_id: str, payload: IntakeRequest, patient_id: str) -> None:
        hh = payload.household
        self.sb.table("household_members").insert(
            {
                "id": str(uuid.uuid4()),
                "household_id": household_id,
                "patient_id": patient_id,
                "relationship": hh.relationship,
                "is_index_case": hh.is_index_case,
            }
        ).execute()

    def _resolve_lookup_ids(self, table: str, items: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Accepts `{id}` or `{name}`. Returns both IDs and names for scoring output.
        """
        ids: list[str] = []
        names: list[str] = []

        raw_ids = [i.get("id") for i in items if i.get("id")]
        raw_names = [i.get("name") for i in items if i.get("name")]

        if raw_ids:
            res = self.sb.table(table).select("id,name").in_("id", raw_ids).execute()
            found = {r["id"]: r for r in (res.data or [])}
            missing = [x for x in raw_ids if x not in found]
            if missing:
                raise ValueError(f"Unknown {table} ids: {missing}")
            for _id, r in found.items():
                ids.append(_id)
                names.append(r.get("name"))

        if raw_names:
            res = self.sb.table(table).select("id,name").in_("name", raw_names).execute()
            found_by_name = {r["name"]: r for r in (res.data or [])}
            missing = [x for x in raw_names if x not in found_by_name]
            if missing:
                raise ValueError(f"Unknown {table} names: {missing}")
            for name, r in found_by_name.items():
                ids.append(r.get("id"))
                names.append(name)

        # de-dupe but keep stable-ish order
        seen: set[str] = set()
        ids2: list[str] = []
        for i in ids:
            if i and i not in seen:
                seen.add(i)
                ids2.append(i)
        names2 = [n for n in dict.fromkeys([n for n in names if n])]

        return {"ids": ids2, "names": names2}

    def _insert_patient_conditions(self, patient_id: str, condition_lookup: dict[str, Any], created_at: datetime) -> None:
        rows = []
        for cid in condition_lookup["ids"]:
            rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "patient_id": patient_id,
                    "condition_id": cid,
                    "status": "active",
                    "recorded_at": created_at.isoformat(),
                }
            )
        if rows:
            self.sb.table("patient_conditions").insert(rows).execute()

    def _insert_patient_symptoms(
        self,
        patient_id: str,
        symptom_lookup: dict[str, Any],
        payload: IntakeRequest,
        created_at: datetime,
    ) -> None:
        if not symptom_lookup["ids"]:
            return

        # Map back severity/duration from payload by id/name
        by_id: dict[str, Any] = {}
        by_name: dict[str, Any] = {}
        for s in payload.symptoms:
            if s.id:
                by_id[s.id] = s
            if s.name:
                by_name[s.name] = s

        # Resolve id->name to pick severity/duration if provided by name
        meta = self.sb.table("symptoms").select("id,name").in_("id", symptom_lookup["ids"]).execute()
        id_to_name = {r["id"]: r.get("name") for r in (meta.data or [])}

        rows = []
        for sid in symptom_lookup["ids"]:
            s_payload = by_id.get(sid) or by_name.get(id_to_name.get(sid))
            severity = getattr(s_payload, "severity", 3) if s_payload else 3
            duration_days = getattr(s_payload, "duration_days", 14) if s_payload else 14
            rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "patient_id": patient_id,
                    "symptom_id": sid,
                    "severity": severity,
                    "duration_days": duration_days,
                    "recorded_at": created_at.isoformat(),
                }
            )
        if rows:
            self.sb.table("patient_symptoms").insert(rows).execute()

    def _save_risk_score(self, patient_id: str, risk_resp: Any, created_at: datetime) -> None:
        self.sb.table("risk_scores").insert(
            {
                "id": str(uuid.uuid4()),
                "patient_id": patient_id,
                "risk_level": risk_resp.risk_level,
                "score": risk_resp.score_normalized,
                "model_version": "rule_based_v1",
                "created_at": created_at.isoformat(),
            }
        ).execute()

