from fastapi import APIRouter, Depends, HTTPException

from app.schemas.consent import ConsentGrantRequest, ConsentOut, ConsentRevokeRequest
from app.services.consent_service import ConsentService

router = APIRouter()


def _svc() -> ConsentService:
    return ConsentService()


@router.post("/{patient_id}/grant", response_model=ConsentOut, status_code=201)
def grant(patient_id: str, payload: ConsentGrantRequest, svc: ConsentService = Depends(_svc)) -> ConsentOut:
    try:
        return svc.grant(patient_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{patient_id}/revoke", response_model=ConsentOut)
def revoke(patient_id: str, payload: ConsentRevokeRequest, svc: ConsentService = Depends(_svc)) -> ConsentOut:
    try:
        out = svc.revoke(patient_id, payload)
        if not out:
            raise HTTPException(status_code=404, detail="Consent not found")
        return out
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{patient_id}", response_model=list[ConsentOut])
def list_for_patient(patient_id: str, svc: ConsentService = Depends(_svc)) -> list[ConsentOut]:
    return svc.list_for_patient(patient_id)

