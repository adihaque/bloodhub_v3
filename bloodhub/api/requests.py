from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from bloodhub.core.database import get_db, DatabaseSession
from bloodhub.models.models import (
    User, BloodRequest, DispatchWave, DonorOffer, Assignment, DonorProfile, DonationRecord, AuditLog, generate_uuid
)
from bloodhub.schemas.schemas import (
    BloodRequestCreate, BloodRequestOut, RequestCancel, DonationConfirm
)
from bloodhub.api.deps import get_optional_current_user, get_current_user
from bloodhub.domain.state_machines import RequestStateMachine, DonorStateMachine
from bloodhub.domain.compatibility import normalize_blood_group
from bloodhub.engine.dispatcher import start_dispatch
from bloodhub.core.security import hash_password

router = APIRouter(prefix="/requests", tags=["Blood Requests"])

@router.post("/", response_model=BloodRequestOut, status_code=status.HTTP_201_CREATED)
def create_blood_request(
    payload: BloodRequestCreate,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: DatabaseSession = Depends(get_db)
):
    norm_blood = normalize_blood_group(payload.blood_group)

    if current_user:
        requester_id = current_user.id
    else:
        clean_phone = payload.contact_phone.strip()
        user = db.query(User).filter_by(phone=clean_phone).first()
        if not user:
            user = User(
                id=generate_uuid(),
                phone=clean_phone,
                full_name=f"Requester ({payload.patient_name.strip()})",
                role="REQUESTER",
                password_hash=hash_password("emergency123"),
                is_active=1,
                is_verified=1,
                created_at=datetime.utcnow().isoformat()
            )
            db.add(user)
            db.flush()
        requester_id = user.id

    now_ts = datetime.utcnow().isoformat()
    new_request = BloodRequest(
        requester_id=requester_id,
        patient_name=payload.patient_name.strip(),
        blood_group=norm_blood,
        component=payload.component.upper(),
        units_needed=payload.units_needed,
        units_fulfilled=0,
        urgency=payload.urgency.upper(),
        hospital_name=payload.hospital_name.strip(),
        hospital_address=payload.hospital_address.strip() if payload.hospital_address else "Dhaka, Bangladesh",
        latitude=payload.latitude,
        longitude=payload.longitude,
        needed_by=payload.needed_by.isoformat() if payload.needed_by else None,
        notes=payload.notes,
        contact_phone=payload.contact_phone.strip(),
        status="MATCHING",
        current_wave=0,
        created_at=now_ts,
        updated_at=now_ts
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    # Immediately activate Wave 1 dispatch using active algorithm
    start_dispatch(db, new_request.id)

    db.refresh(new_request)
    return new_request.to_dict()

@router.get("/{request_id}")
def get_blood_request_detail(
    request_id: str,
    db: DatabaseSession = Depends(get_db)
):
    req = db.query(BloodRequest).filter_by(id=request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Blood request not found")

    assigned = db.query(Assignment).filter_by(request_id=req.id).all()
    assigned_donors = []
    for a in assigned:
        d_user = db.query(User).filter_by(id=a.donor_id).first()
        d_prof = db.query(DonorProfile).filter_by(user_id=a.donor_id).first()
        if d_user and d_prof:
            assigned_donors.append({
                "assignment_id": a.id,
                "donor_name": d_user.full_name,
                "donor_phone": d_user.phone,
                "donor_whatsapp": d_prof.whatsapp_number or d_user.phone,
                "blood_group": d_prof.blood_group,
                "assigned_at": a.assigned_at
            })

    active_wave = db.query(DispatchWave).filter("request_id = ? AND status = 'ACTIVE'", [req.id]).first()
    offers_count = db.query(DonorOffer).filter_by(request_id=req.id).count()

    result = req.to_dict()
    result["assigned_donors"] = assigned_donors
    result["active_wave_info"] = active_wave.to_dict() if active_wave else None
    result["total_offers_sent"] = offers_count
    return result

@router.post("/{request_id}/cancel")
def cancel_blood_request(
    request_id: str,
    payload: RequestCancel,
    db: DatabaseSession = Depends(get_db)
):
    req = db.query(BloodRequest).filter_by(id=request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Blood request not found")

    if req.status in ("COMPLETED", "CANCELLED"):
        return {"status": req.status, "message": "Request is already finished or cancelled."}

    req.status = "CANCELLED"
    db.add(req)

    # Cancel active offers and restore donors to AVAILABLE
    active_offers = db.query(DonorOffer).filter("request_id = ? AND status = 'OFFERED'", [req.id]).all()
    for o in active_offers:
        o.status = "REVOKED"
        db.add(o)
        prof = db.query(DonorProfile).filter_by(user_id=o.donor_id).first()
        if prof and prof.availability_status == "OFFERED":
            prof.availability_status = "AVAILABLE"
            db.add(prof)

    db.commit()
    return {"status": "CANCELLED", "message": "Request successfully cancelled."}
