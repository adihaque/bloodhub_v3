from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from bloodhub.core.config import settings
from bloodhub.core.database import get_db, DatabaseSession
from bloodhub.models.models import (
    User, DonorProfile, BloodRequest, DispatchWave, DonorOffer, Assignment, AuditLog
)
from bloodhub.schemas.schemas import SystemMetricsOut, AuditLogOut
from bloodhub.api.deps import require_admin

router = APIRouter(prefix="/admin", tags=["Administration"])

@router.get("/metrics", response_model=SystemMetricsOut)
def get_system_metrics(
    current_admin: User = Depends(require_admin),
    db: DatabaseSession = Depends(get_db)
):
    total_donors = db.query(DonorProfile).count()
    available_donors = db.query(DonorProfile).filter_by(availability_status="AVAILABLE").count()
    total_requests = db.query(BloodRequest).count()
    active_requests = db.query(BloodRequest).filter("status IN ('MATCHING', 'AWAITING_DONOR', 'ACTIVE')").count()
    fulfilled_requests = db.query(BloodRequest).filter("status IN ('ASSIGNED', 'CONFIRMED', 'COMPLETED')").count()
    total_assignments = db.query(Assignment).count()
    active_waves = db.query(DispatchWave).filter_by(status="ACTIVE").count()

    total_offers = db.query(DonorOffer).count()
    accepted_offers = db.query(DonorOffer).filter_by(status="ACCEPTED").count()
    acceptance_rate = round((accepted_offers / total_offers) * 100, 1) if total_offers > 0 else 0.0

    return {
        "total_donors": total_donors,
        "available_donors": available_donors,
        "total_requests": total_requests,
        "active_requests": active_requests,
        "fulfilled_requests": fulfilled_requests,
        "total_assignments": total_assignments,
        "acceptance_rate": acceptance_rate,
        "active_waves": active_waves,
        "active_environment": settings.ENVIRONMENT
    }

@router.get("/donors")
def list_registered_donors(
    current_admin: User = Depends(require_admin),
    db: DatabaseSession = Depends(get_db)
):
    """Returns real registered donors with contact details for platform operations."""
    users = db.query(User).filter_by(role="DONOR").order_by("created_at DESC").all()
    results = []
    for u in users:
        p = db.query(DonorProfile).filter_by(user_id=u.id).first()
        results.append({
            "user_id": u.id,
            "full_name": u.full_name,
            "phone": u.phone,
            "email": u.email,
            "whatsapp_number": p.whatsapp_number if p else None,
            "blood_group": p.blood_group if p else "N/A",
            "donation_intent": p.donation_intent if p else "REGULAR",
            "area_district": p.area_district if p else "N/A",
            "availability_status": p.availability_status if p else "N/A",
            "last_donation_date": p.last_donation_date if p else None,
            "total_donations": p.total_donations if p else 0,
            "is_active": bool(u.is_active),
            "created_at": u.created_at
        })
    return results

@router.get("/audit-logs", response_model=List[AuditLogOut])
def get_audit_logs(
    limit: int = Query(50, le=200),
    current_admin: User = Depends(require_admin),
    db: DatabaseSession = Depends(get_db)
):
    logs = db.query(AuditLog).order_by("created_at DESC").limit(limit).all()
    return [l.to_dict() for l in logs]

@router.put("/users/{user_id}/suspend")
def suspend_user(
    user_id: str,
    current_admin: User = Depends(require_admin),
    db: DatabaseSession = Depends(get_db)
):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = 0
    db.add(user)
    profile = db.query(DonorProfile).filter_by(user_id=user.id).first()
    if profile:
        profile.availability_status = "SUSPENDED"
        db.add(profile)

    audit = AuditLog(
        user_id=current_admin.id,
        action="USER_SUSPENDED",
        resource_type="User",
        resource_id=user.id,
        details=f"Admin {current_admin.full_name} suspended user {user.full_name} ({user.phone})."
    )
    db.add(audit)
    db.commit()
    return {"status": "SUSPENDED", "message": f"User {user.full_name} has been suspended."}

@router.put("/users/{user_id}/activate")
def activate_user(
    user_id: str,
    current_admin: User = Depends(require_admin),
    db: DatabaseSession = Depends(get_db)
):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = 1
    db.add(user)
    profile = db.query(DonorProfile).filter_by(user_id=user.id).first()
    if profile:
        profile.availability_status = "AVAILABLE"
        db.add(profile)

    audit = AuditLog(
        user_id=current_admin.id,
        action="USER_ACTIVATED",
        resource_type="User",
        resource_id=user.id,
        details=f"Admin {current_admin.full_name} reactivated user {user.full_name}."
    )
    db.add(audit)
    db.commit()
    return {"status": "ACTIVE", "message": f"User {user.full_name} has been activated."}
