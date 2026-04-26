from fastapi import APIRouter, Depends, HTTPException

from app.schemas.households import HouseholdCreate, HouseholdMemberLink, HouseholdOut
from app.services.household_service import HouseholdService

router = APIRouter()


def _svc() -> HouseholdService:
    return HouseholdService()


@router.post("", response_model=HouseholdOut, status_code=201)
def create_household(payload: HouseholdCreate, svc: HouseholdService = Depends(_svc)) -> HouseholdOut:
    return svc.create_household(payload)


@router.get("/{household_id}", response_model=HouseholdOut)
def get_household(household_id: str, svc: HouseholdService = Depends(_svc)) -> HouseholdOut:
    hh = svc.get_household(household_id)
    if not hh:
        raise HTTPException(status_code=404, detail="Household not found")
    return hh


@router.post("/{household_id}/members", status_code=201)
def link_member(household_id: str, payload: HouseholdMemberLink, svc: HouseholdService = Depends(_svc)) -> dict:
    try:
        return svc.link_member(household_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

