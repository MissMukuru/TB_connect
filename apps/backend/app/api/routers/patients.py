from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.patients import PatientCreate, PatientOut, PatientUpdate
from app.services.patients_service import PatientsService

router = APIRouter()


def _svc() -> PatientsService:
    return PatientsService()


@router.post("", response_model=PatientOut, status_code=201)
def create_patient(payload: PatientCreate, svc: PatientsService = Depends(_svc)) -> PatientOut:
    try:
        return svc.create_patient(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: str, svc: PatientsService = Depends(_svc)) -> PatientOut:
    patient = svc.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.get("", response_model=list[PatientOut])
def list_patients(
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    svc: PatientsService = Depends(_svc),
) -> list[PatientOut]:
    return svc.list_patients(limit=limit, offset=offset)


@router.patch("/{patient_id}", response_model=PatientOut)
def update_patient(patient_id: str, payload: PatientUpdate, svc: PatientsService = Depends(_svc)) -> PatientOut:
    updated = svc.update_patient(patient_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Patient not found")
    return updated


@router.delete("/{patient_id}", status_code=204)
def delete_patient(patient_id: str, svc: PatientsService = Depends(_svc)) -> None:
    ok = svc.delete_patient(patient_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Patient not found")
    return None

