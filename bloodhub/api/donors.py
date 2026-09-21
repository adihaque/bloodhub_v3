from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from bloodhub.core.database import get_db, DatabaseSession
from bloodhub.models.models import User, DonorProfile, DonorOffer, BloodRequest, AuditLog
from bloodhub.schemas.schemas import (
    DonorProfileOut, DonorProfileUpdate, LocationUpdate, AvailabilityUpdate,
    DonorOfferOut, OfferResponse
)
from bloodhub.api.deps import get_current_user
from bloodhub.domain.state_machines import DonorStateMachine
from bloodhub.domain.compatibility import normalize_blood_group
from bloodhub.domain.geospatial import haversine_distance
from bloodhub.engine.concurrency import atomic_accept_offer

router = APIRouter(prefix="/donors", tags=["Donors"])

def _compose_donor_response(user: User, profile: DonorProfile) -> dict:
    data = profile.to_dict()
    data["full_name"] = user.full_name
    data["phone"] = user.phone
    data["email"] = user.email
    return data

@router.get("/profile", response_model=DonorProfileOut)
def get_donor_profile(
    current_user: User = Depends(get_current_user),
    db: DatabaseSession = Depends(get_db)
):
    profile = db.query(DonorProfile).filter_by(user_id=current_user.id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Donor profile does not exist for this account."
        )
    return _compose_donor_response(current_user, profile)

@router.put("/profile", response_model=DonorProfileOut)
def update_donor_profile(
    payload: DonorProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: DatabaseSession = Depends(get_db)
):
    """
    Updates the donor profile in real-time.
    Survives app refresh and server restart.
    """
    profile = db.query(DonorProfile).filter_by(user_id=current_user.id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Donor profile not found."
        )

    # 1. User name update
    if payload.full_name and payload.full_name.strip():
        current_user.full_name = payload.full_name.strip()
        db.add(current_user)

    # 2. Donor Profile fields update
    if payload.blood_group:
        profile.blood_group = normalize_blood_group(payload.blood_group)

    if payload.whatsapp_number is not None:
        profile.whatsapp_number = payload.whatsapp_number.strip()

    if payload.donation_intent:
        profile.donation_intent = payload.donation_intent.upper()

    if payload.last_donation_date is not None:
        profile.last_donation_date = payload.last_donation_date.strip() or None

    if payload.area_district:
        profile.area_district = payload.area_district.strip()

    if payload.weight_kg is not None:
        profile.weight_kg = payload.weight_kg

    if payload.preferred_radius_km is not None:
        profile.preferred_radius_km = payload.preferred_radius_km

    if payload.latitude is not None and payload.longitude is not None:
        profile.latitude = payload.latitude
        profile.longitude = payload.longitude

    if payload.availability_status:
        target_status = payload.availability_status.upper()
        DonorStateMachine.validate_transition(profile.availability_status, target_status)
        profile.availability_status = target_status

    db.add(profile)

    audit = AuditLog(
        user_id=current_user.id,
        action="DONOR_PROFILE_UPDATED",
        resource_type="DonorProfile",
        resource_id=profile.id,
        details="Donor updated personal profile in real-time."
    )
    db.add(audit)
    db.commit()
    db.refresh(profile)
    db.refresh(current_user)

    return _compose_donor_response(current_user, profile)

@router.put("/location", response_model=DonorProfileOut)
def update_donor_location(
    payload: LocationUpdate,
    current_user: User = Depends(get_current_user),
    db: DatabaseSession = Depends(get_db)
):
    profile = db.query(DonorProfile).filter_by(user_id=current_user.id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Donor profile not found."
        )
    profile.latitude = payload.latitude
    profile.longitude = payload.longitude
    if payload.address:
        profile.address = payload.address
    if payload.area_district:
        profile.area_district = payload.area_district
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _compose_donor_response(current_user, profile)

@router.put("/availability", response_model=DonorProfileOut)
def update_donor_availability(
    payload: AvailabilityUpdate,
    current_user: User = Depends(get_current_user),
    db: DatabaseSession = Depends(get_db)
):
    profile = db.query(DonorProfile).filter_by(user_id=current_user.id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Donor profile not found."
        )
    
    target_status = payload.availability_status.upper()
    DonorStateMachine.validate_transition(profile.availability_status, target_status)
    profile.availability_status = target_status
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _compose_donor_response(current_user, profile)

@router.get("/offers", response_model=List[DonorOfferOut])
def get_incoming_offers(
    current_user: User = Depends(get_current_user),
    db: DatabaseSession = Depends(get_db)
):
    now = datetime.utcnow()
    offers = db.query(DonorOffer).filter(
        "donor_id = ? AND status = 'OFFERED' AND expires_at > ?",
        [current_user.id, now.isoformat()]
    ).all()

    profile = db.query(DonorProfile).filter_by(user_id=current_user.id).first()

    results = []
    for offer in offers:
        request = db.query(BloodRequest).filter_by(id=offer.request_id).first()
        if not request:
            continue

        dist_km = 0.0
        if profile:
            dist_km = haversine_distance(
                request.latitude, request.longitude,
                profile.latitude, profile.longitude
            )

        exp_dt = datetime.fromisoformat(offer.expires_at) if isinstance(offer.expires_at, str) else offer.expires_at
        seconds_left = max(0, int((exp_dt - now).total_seconds()))

        results.append({
            "id": offer.id,
            "wave_id": offer.wave_id,
            "request_id": offer.request_id,
            "donor_id": offer.donor_id,
            "status": offer.status,
            "sent_at": offer.sent_at,
            "expires_at": offer.expires_at,
            "seconds_remaining": seconds_left,
            "hospital_name": request.hospital_name,
            "hospital_address": request.hospital_address,
            "patient_name": request.patient_name,
            "blood_group": request.blood_group,
            "urgency": request.urgency,
            "distance_km": dist_km
        })
    return results

@router.post("/offers/{offer_id}/accept")
def accept_incoming_offer(
    offer_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseSession = Depends(get_db)
):
    res = atomic_accept_offer(db, offer_id=offer_id, donor_id=current_user.id)
    if not res["success"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=res["message"]
        )
    return res

@router.post("/offers/{offer_id}/reject")
def reject_incoming_offer(
    offer_id: str,
    payload: OfferResponse,
    current_user: User = Depends(get_current_user),
    db: DatabaseSession = Depends(get_db)
):
    offer = db.query(DonorOffer).filter(
        "id = ? AND donor_id = ?", [offer_id, current_user.id]
    ).first()

    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    if offer.status != "OFFERED":
        raise HTTPException(status_code=400, detail=f"Offer is not in OFFERED status (currently '{offer.status}')")

    offer.status = "REJECTED"
    offer.responded_at = datetime.utcnow().isoformat()
    offer.rejection_reason = payload.rejection_reason or "Donor declined"
    db.add(offer)

    profile = db.query(DonorProfile).filter_by(user_id=current_user.id).first()
    if profile:
        profile.availability_status = "AVAILABLE"
        profile.rejected_count = int(profile.rejected_count or 0) + 1
        db.add(profile)

    audit = AuditLog(
        user_id=current_user.id,
        action="OFFER_REJECTED",
        resource_type="DonorOffer",
        resource_id=offer.id,
        details=f"Donor rejected offer for request {offer.request_id}."
    )
    db.add(audit)
    db.commit()

    return {"status": "REJECTED", "message": "Offer rejected successfully."}
