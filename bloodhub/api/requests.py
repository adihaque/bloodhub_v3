from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from bloodhub.core.database import get_db, DatabaseSession
from bloodhub.models.models import (
    User, BloodRequest, DispatchWave, DonorOffer, Assignment, DonorProfile, DonationRecord, AuditLog
)
from bloodhub.schemas.schemas import (
    BloodRequestCreate, BloodRequestOut, RequestCancel, DonationConfirm
)
from bloodhub.api.deps import get_current_user
from bloodhub.domain.state_machines import RequestStateMachine, DonorStateMachine
from bloodhub.domain.compatibility import normalize_blood_group
from bloodhub.engine.dispatcher import start_dispatch
from bloodhub.providers.notifications.console import ConsoleNotificationProvider

notification_provider = ConsoleNotificationProvider()
router = APIRouter(prefix="/requests", tags=["Blood Requests"])

@router.post("/", response_model=BloodRequestOut, status_code=status.HTTP_201_CREATED)
def create_blood_request(
    payload: BloodRequestCreate,
    current_user: User = Depends(get_current_user),
    db: DatabaseSession = Depends(get_db)
):
    norm_blood = normalize_blood_group(payload.blood_group)
    new_request = BloodRequest(
        requester_id=current_user.id,
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
        status="ACTIVE",
        current_wave=0
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    # Immediately trigger automated wave dispatch
    start_dispatch(db, new_request.id)
    db.refresh(new_request)

    audit = AuditLog(
        user_id=current_user.id,
        action="REQUEST_CREATED",
        resource_type="BloodRequest",
        resource_id=new_request.id,
        details=f"Created request for {new_request.units_needed} unit(s) of {new_request.blood_group} at {new_request.hospital_name}."
    )
    db.add(audit)
    db.commit()

    return new_request.to_dict()

@router.get("/", response_model=List[BloodRequestOut])
def list_blood_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    blood_group: Optional[str] = Query(None),
    urgency: Optional[str] = Query(None),
    db: DatabaseSession = Depends(get_db)
):
    builder = db.query(BloodRequest)
    if status_filter:
        builder.filter("status = ?", [status_filter.upper()])
    if blood_group:
        builder.filter("blood_group = ?", [normalize_blood_group(blood_group)])
    if urgency:
        builder.filter("urgency = ?", [urgency.upper()])
    
    requests = builder.order_by("created_at DESC").limit(100).all()
    return [r.to_dict() for r in requests]

@router.get("/{request_id}")
def get_blood_request_detail(
    request_id: str,
    db: DatabaseSession = Depends(get_db)
):
    request = db.query(BloodRequest).filter_by(id=request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Blood request not found")

    # Fetch active wave info
    latest_wave = (
        db.query(DispatchWave)
        .filter_by(request_id=request.id)
        .order_by("wave_number DESC")
        .first()
    )

    # Fetch assignments
    assignments = db.query(Assignment).filter_by(request_id=request.id).all()
    assigned_donors = []
    for asm in assignments:
        donor_user = db.query(User).filter_by(id=asm.donor_id).first()
        donor_prof = db.query(DonorProfile).filter_by(user_id=asm.donor_id).first()
        if donor_user and donor_prof:
            assigned_donors.append({
                "assignment_id": asm.id,
                "donor_name": donor_user.full_name,
                "donor_phone": donor_user.phone,
                "blood_group": donor_prof.blood_group,
                "status": asm.status,
                "assigned_at": asm.assigned_at
            })

    return {
        "id": request.id,
        "patient_name": request.patient_name,
        "blood_group": request.blood_group,
        "component": request.component,
        "units_needed": request.units_needed,
        "units_fulfilled": request.units_fulfilled,
        "urgency": request.urgency,
        "hospital_name": request.hospital_name,
        "hospital_address": request.hospital_address,
        "latitude": request.latitude,
        "longitude": request.longitude,
        "contact_phone": request.contact_phone,
        "status": request.status,
        "current_wave": request.current_wave,
        "created_at": request.created_at,
        "latest_wave": {
            "wave_number": latest_wave.wave_number if latest_wave else 0,
            "radius_km": latest_wave.radius_km if latest_wave else 0,
            "candidate_count": latest_wave.candidate_count if latest_wave else 0,
            "status": latest_wave.status if latest_wave else "NONE",
            "expires_at": latest_wave.expires_at if latest_wave else None
        } if latest_wave else None,
        "assigned_donors": assigned_donors
    }

@router.post("/{request_id}/cancel")
def cancel_blood_request(
    request_id: str,
    payload: RequestCancel,
    current_user: User = Depends(get_current_user),
    db: DatabaseSession = Depends(get_db)
):
    request = db.query(BloodRequest).filter_by(id=request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Blood request not found")

    if current_user.role != "ADMIN" and request.requester_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the requester or an administrator can cancel this request.")

    RequestStateMachine.validate_transition(request.status, "CANCELLED")
    request.status = "CANCELLED"
    db.add(request)

    # Revoke all open offers
    open_offers = db.query(DonorOffer).filter(
        "request_id = ? AND status = 'OFFERED'", [request.id]
    ).all()

    alerted_donors = []
    for off in open_offers:
        off.status = "REVOKED"
        db.add(off)
        prof = db.query(DonorProfile).filter_by(user_id=off.donor_id).first()
        if prof and prof.availability_status == "OFFERED":
            prof.availability_status = "AVAILABLE"
            db.add(prof)
        alerted_donors.append(off.donor_id)

    # Cancel active assignments
    assignments = db.query(Assignment).filter(
        "request_id = ? AND status = 'ACTIVE'", [request.id]
    ).all()

    for asm in assignments:
        asm.status = "CANCELLED"
        db.add(asm)
        donor_prof = db.query(DonorProfile).filter_by(user_id=asm.donor_id).first()
        if donor_prof and donor_prof.availability_status == "ASSIGNED":
            donor_prof.availability_status = "AVAILABLE"
            donor_prof.active_assignment_id = None
            db.add(donor_prof)
        alerted_donors.append(asm.donor_id)

    notification_provider.send_request_cancellation(alerted_donors, request.id)

    audit = AuditLog(
        user_id=current_user.id,
        action="REQUEST_CANCELLED",
        resource_type="BloodRequest",
        resource_id=request.id,
        details=f"Request cancelled: {payload.reason}"
    )
    db.add(audit)
    db.commit()

    return {"status": "CANCELLED", "message": "Blood request successfully cancelled and donors notified."}

@router.post("/{request_id}/confirm")
def confirm_donation_completion(
    request_id: str,
    payload: DonationConfirm,
    current_user: User = Depends(get_current_user),
    db: DatabaseSession = Depends(get_db)
):
    request = db.query(BloodRequest).filter_by(id=request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Blood request not found")

    assignment = db.query(Assignment).filter(
        "request_id = ? AND status = 'ACTIVE'", [request.id]
    ).first()

    if not assignment:
        raise HTTPException(status_code=400, detail="No active assignment found to confirm.")

    now = datetime.utcnow()
    assignment.status = "COMPLETED"
    assignment.completed_at = now.isoformat()
    assignment.notes = payload.notes
    db.add(assignment)

    record = DonationRecord(
        assignment_id=assignment.id,
        request_id=request.id,
        donor_id=assignment.donor_id,
        hospital_name=request.hospital_name,
        units_donated=1,
        donation_date=now.isoformat(),
        verified_by_admin_id=current_user.id
    )
    db.add(record)

    donor_profile = db.query(DonorProfile).filter_by(user_id=assignment.donor_id).first()
    if donor_profile:
        donor_profile.availability_status = "AVAILABLE"
        donor_profile.active_assignment_id = None
        donor_profile.total_donations = int(donor_profile.total_donations) + 1
        donor_profile.last_donation_date = now.strftime("%Y-%m-%d")
        db.add(donor_profile)

    RequestStateMachine.validate_transition(request.status, "COMPLETED")
    request.status = "COMPLETED"
    db.add(request)

    audit = AuditLog(
        user_id=current_user.id,
        action="DONATION_CONFIRMED",
        resource_type="DonationRecord",
        resource_id=record.id,
        details=f"Donation completed for request {request.id} by donor {assignment.donor_id}."
    )
    db.add(audit)
    db.commit()

    return {
        "status": "COMPLETED",
        "message": "Donation successfully confirmed. Donor cooldown and donation history updated."
    }
