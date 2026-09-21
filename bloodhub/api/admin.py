import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from bloodhub.core.config import settings
from bloodhub.core.database import get_db, DatabaseSession
from bloodhub.models.models import (
    User, DonorProfile, BloodRequest, DispatchWave, DonorOffer, Assignment, AuditLog, AlgorithmConfig
)
from bloodhub.schemas.schemas import (
    SystemMetricsOut, AuditLogOut, AlgorithmConfigOut, AlgorithmConfigUpdate, AlgorithmPreviewRequest
)
from bloodhub.api.deps import require_admin
from bloodhub.domain.compatibility import get_compatible_donor_groups, normalize_blood_group
from bloodhub.domain.eligibility import check_donor_eligibility
from bloodhub.domain.geospatial import haversine_distance
from bloodhub.domain.ranking import calculate_candidate_score
from bloodhub.engine.dispatcher import get_active_algorithm_config, progress_wave

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

# =======================================================
# ALGORITHM MANAGEMENT & REAL-TIME CONFIGURATION
# =======================================================

@router.get("/algorithm", response_model=AlgorithmConfigOut)
def get_algorithm_configuration(
    current_admin: User = Depends(require_admin),
    db: DatabaseSession = Depends(get_db)
):
    """Fetches the active algorithm configuration and weights from the database."""
    cfg = get_active_algorithm_config(db)
    return cfg.to_dict()

@router.put("/algorithm", response_model=AlgorithmConfigOut)
def update_algorithm_configuration(
    payload: AlgorithmConfigUpdate,
    current_admin: User = Depends(require_admin),
    db: DatabaseSession = Depends(get_db)
):
    """
    Updates the algorithm weights, candidate limits, and wave parameters in real-time.
    Immediately alters candidate ranking and dispatch behavior for subsequent requests.
    """
    cfg = db.query(AlgorithmConfig).filter_by(id="active_config").first()
    if not cfg:
        cfg = AlgorithmConfig(id="active_config")

    data = payload.dict(exclude_unset=True)
    changed_keys = []
    for k, v in data.items():
        if v is not None:
            setattr(cfg, k, v)
            changed_keys.append(f"{k}={v}")

    cfg.updated_at = datetime.utcnow().isoformat()
    cfg.updated_by = current_admin.full_name
    db.add(cfg)

    audit = AuditLog(
        user_id=current_admin.id,
        action="ALGORITHM_UPDATED",
        resource_type="AlgorithmConfig",
        resource_id="active_config",
        details=f"Admin updated algorithm weights: {', '.join(changed_keys)}"
    )
    db.add(audit)
    db.commit()
    db.refresh(cfg)
    return cfg.to_dict()

@router.post("/algorithm/reset", response_model=AlgorithmConfigOut)
def reset_algorithm_configuration(
    current_admin: User = Depends(require_admin),
    db: DatabaseSession = Depends(get_db)
):
    """Resets all algorithm parameters and wave definitions back to default clinical baseline."""
    cfg = db.query(AlgorithmConfig).filter_by(id="active_config").first()
    if not cfg:
        cfg = AlgorithmConfig(id="active_config")

    defaults = {
        "compatibility_exact_pts": 40.0,
        "compatibility_compatible_pts": 25.0,
        "proximity_weight_pts": 35.0,
        "reliability_weight_pts": 15.0,
        "interval_weight_pts": 10.0,
        "intent_regular_bonus": 5.0,
        "intent_when_needed_bonus": 2.0,
        "cooldown_days": 90,
        "wave1_radius_km": 5.0,
        "wave1_timeout_sec": 25,
        "wave1_candidates": 4,
        "wave2_radius_km": 8.0,
        "wave2_timeout_sec": 25,
        "wave2_candidates": 6,
        "wave3_radius_km": 15.0,
        "wave3_timeout_sec": 30,
        "wave3_candidates": 10,
        "wave4_radius_km": 25.0,
        "wave4_timeout_sec": 35,
        "wave4_candidates": 15,
        "auto_dispatch_whatsapp": 1,
        "auto_dispatch_in_app": 1,
        "auto_dispatch_sms": 1,
        "updated_at": datetime.utcnow().isoformat(),
        "updated_by": f"{current_admin.full_name} (Reset)"
    }
    for k, v in defaults.items():
        setattr(cfg, k, v)

    db.add(cfg)
    audit = AuditLog(
        user_id=current_admin.id,
        action="ALGORITHM_RESET",
        resource_type="AlgorithmConfig",
        resource_id="active_config",
        details="Admin reset algorithm weights to clinical defaults."
    )
    db.add(audit)
    db.commit()
    db.refresh(cfg)
    return cfg.to_dict()

@router.post("/algorithm/preview")
def preview_algorithm_calculation(
    payload: AlgorithmPreviewRequest,
    current_admin: User = Depends(require_admin),
    db: DatabaseSession = Depends(get_db)
):
    """
    Simulates the algorithm calculation over the entire active donor database.
    Shows the step-by-step mathematical score breakdown and filtering reasons for every donor.
    """
    cfg = get_active_algorithm_config(db)
    norm_blood = normalize_blood_group(payload.blood_group)
    comp_groups = get_compatible_donor_groups(norm_blood, payload.component)

    all_profiles = db.query(DonorProfile).all()
    
    eligible_candidates = []
    excluded_candidates = []

    for prof in all_profiles:
        u = db.query(User).filter_by(id=prof.user_id).first()
        if not u or not u.is_active:
            excluded_candidates.append({
                "donor_name": u.full_name if u else "Unknown",
                "blood_group": prof.blood_group,
                "reason": "Account is inactive or suspended"
            })
            continue

        # 1. Compatibility Check
        if prof.blood_group not in comp_groups:
            excluded_candidates.append({
                "donor_name": u.full_name,
                "blood_group": prof.blood_group,
                "phone": u.phone,
                "area": prof.area_district,
                "reason": f"Incompatible blood group ({prof.blood_group} cannot give to {norm_blood})"
            })
            continue

        # 2. Availability Check
        if prof.availability_status != "AVAILABLE":
            excluded_candidates.append({
                "donor_name": u.full_name,
                "blood_group": prof.blood_group,
                "phone": u.phone,
                "area": prof.area_district,
                "reason": f"Status is {prof.availability_status} (not AVAILABLE)"
            })
            continue

        # 3. Medical Cooldown Check
        eligible, reason = check_donor_eligibility(
            availability_status=prof.availability_status,
            weight_kg=prof.weight_kg,
            birth_date_str=prof.date_of_birth,
            last_donation_date_str=prof.last_donation_date,
            gender=prof.gender,
            component=payload.component,
            active_assignment_id=prof.active_assignment_id
        )
        if not eligible:
            excluded_candidates.append({
                "donor_name": u.full_name,
                "blood_group": prof.blood_group,
                "phone": u.phone,
                "area": prof.area_district,
                "reason": reason
            })
            continue

        # 4. Distance Calculation
        dist_km = haversine_distance(payload.latitude, payload.longitude, prof.latitude, prof.longitude)
        if dist_km > payload.radius_km:
            excluded_candidates.append({
                "donor_name": u.full_name,
                "blood_group": prof.blood_group,
                "phone": u.phone,
                "area": prof.area_district,
                "reason": f"Distance {dist_km:.2f} km exceeds target radius {payload.radius_km:.1f} km"
            })
            continue

        # 5. Score Calculation
        score_info = calculate_candidate_score(
            donor_blood_group=prof.blood_group,
            recipient_blood_group=norm_blood,
            distance_km=dist_km,
            max_radius_km=payload.radius_km,
            reliability_score=prof.reliability_score,
            last_donation_date_str=prof.last_donation_date,
            donation_intent=prof.donation_intent or "REGULAR",
            config=cfg
        )

        eligible_candidates.append({
            "donor_id": u.id,
            "donor_name": u.full_name,
            "phone": u.phone,
            "whatsapp_number": prof.whatsapp_number or u.phone,
            "blood_group": prof.blood_group,
            "area": prof.area_district,
            "distance_km": round(dist_km, 2),
            "score": score_info["total_score"],
            "breakdown": score_info["breakdown"],
            "donation_intent": prof.donation_intent or "REGULAR",
            "last_donation": prof.last_donation_date or "First-time donor"
        })

    # Sort descending by composite score, then by distance
    eligible_candidates.sort(key=lambda x: (-x["score"], x["distance_km"]))

    # Assign ranks
    for rank_idx, cand in enumerate(eligible_candidates, 1):
        cand["rank"] = rank_idx

    return {
        "request_params": {
            "blood_group": norm_blood,
            "component": payload.component,
            "hospital": payload.hospital_name,
            "radius_km": payload.radius_km
        },
        "summary": {
            "total_donors_in_db": len(all_profiles),
            "eligible_count": len(eligible_candidates),
            "excluded_count": len(excluded_candidates),
            "top_candidates_selected": min(len(eligible_candidates), payload.max_candidates)
        },
        "ranked_candidates": eligible_candidates[:payload.max_candidates],
        "excluded_candidates": excluded_candidates
    }

# =======================================================
# REQUEST AUDIT & DISPATCH PROCESS INSPECTION
# =======================================================

@router.get("/requests")
def list_all_requests(
    current_admin: User = Depends(require_admin),
    db: DatabaseSession = Depends(get_db)
):
    """Lists all blood requests with operational status and wave counters."""
    reqs = db.query(BloodRequest).order_by("created_at DESC").all()
    results = []
    for r in reqs:
        req_user = db.query(User).filter_by(id=r.requester_id).first()
        active_wave = db.query(DispatchWave).filter("request_id = ? AND status = 'ACTIVE'", [r.id]).first()
        offers_count = db.query(DonorOffer).filter_by(request_id=r.id).count()
        accepted_offer = db.query(DonorOffer).filter("request_id = ? AND status = 'ACCEPTED'", [r.id]).first()

        results.append({
            "id": r.id,
            "patient_name": r.patient_name,
            "blood_group": r.blood_group,
            "component": r.component,
            "hospital_name": r.hospital_name,
            "hospital_address": r.hospital_address,
            "status": r.status,
            "current_wave": r.current_wave,
            "units_needed": r.units_needed,
            "units_fulfilled": r.units_fulfilled,
            "requester_name": req_user.full_name if req_user else "Requester",
            "contact_phone": r.contact_phone,
            "total_offers_sent": offers_count,
            "has_accepted_donor": bool(accepted_offer),
            "created_at": r.created_at
        })
    return results

@router.get("/requests/{request_id}/inspection")
def inspect_request_dispatch(
    request_id: str,
    current_admin: User = Depends(require_admin),
    db: DatabaseSession = Depends(get_db)
):
    """
    Detailed audit inspector for an emergency request:
    Shows how the algorithm calculated scores, which donors were ranked,
    which channels were dispatched (In-App, WhatsApp, SMS), and exact response latency.
    """
    req = db.query(BloodRequest).filter_by(id=request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Blood request not found")

    requester = db.query(User).filter_by(id=req.requester_id).first()
    waves = db.query(DispatchWave).filter_by(request_id=req.id).order_by("wave_number ASC").all()

    waves_data = []
    for w in waves:
        offers = db.query(DonorOffer).filter_by(wave_id=w.id).all()
        offers_data = []
        for o in offers:
            d_user = db.query(User).filter_by(id=o.donor_id).first()
            d_prof = db.query(DonorProfile).filter_by(user_id=o.donor_id).first()
            breakdown_dict = {}
            if o.score_breakdown:
                try:
                    breakdown_dict = json.loads(o.score_breakdown)
                except Exception:
                    pass

            offers_data.append({
                "offer_id": o.id,
                "donor_id": o.donor_id,
                "donor_name": d_user.full_name if d_user else "Donor",
                "donor_phone": d_user.phone if d_user else "N/A",
                "whatsapp_number": d_prof.whatsapp_number if d_prof else None,
                "blood_group": d_prof.blood_group if d_prof else "N/A",
                "donation_intent": d_prof.donation_intent if d_prof else "REGULAR",
                "area": d_prof.area_district if d_prof else "N/A",
                "score": o.score,
                "score_breakdown": breakdown_dict,
                "distance_km": o.distance_km,
                "channels": o.channels or "IN_APP,WHATSAPP,SMS",
                "whatsapp_url": o.whatsapp_url,
                "status": o.status,
                "sent_at": o.sent_at,
                "responded_at": o.responded_at,
                "response_latency_seconds": o.response_latency_seconds,
                "rejection_reason": o.rejection_reason
            })

        waves_data.append({
            "wave_id": w.id,
            "wave_number": w.wave_number,
            "radius_km": w.radius_km,
            "timeout_seconds": w.timeout_seconds,
            "status": w.status,
            "started_at": w.started_at,
            "expires_at": w.expires_at,
            "candidate_count": len(offers_data),
            "offers": offers_data
        })

    # Assigned Donor (if matched)
    assignment = db.query(Assignment).filter_by(request_id=req.id).first()
    assignment_data = None
    if assignment:
        winner_user = db.query(User).filter_by(id=assignment.donor_id).first()
        winner_prof = db.query(DonorProfile).filter_by(user_id=assignment.donor_id).first()
        assignment_data = {
            "assignment_id": assignment.id,
            "donor_name": winner_user.full_name if winner_user else "Donor",
            "donor_phone": winner_user.phone if winner_user else "N/A",
            "donor_whatsapp": winner_prof.whatsapp_number if winner_prof else None,
            "donor_blood_group": winner_prof.blood_group if winner_prof else req.blood_group,
            "assigned_at": assignment.assigned_at,
            "status": assignment.status
        }

    return {
        "request": {
            "id": req.id,
            "patient_name": req.patient_name,
            "blood_group": req.blood_group,
            "component": req.component,
            "units_needed": req.units_needed,
            "units_fulfilled": req.units_fulfilled,
            "hospital_name": req.hospital_name,
            "hospital_address": req.hospital_address,
            "latitude": req.latitude,
            "longitude": req.longitude,
            "urgency": req.urgency,
            "contact_phone": req.contact_phone,
            "requester_name": requester.full_name if requester else "Requester",
            "status": req.status,
            "current_wave": req.current_wave,
            "created_at": req.created_at
        },
        "waves": waves_data,
        "assignment": assignment_data
    }

@router.post("/requests/{request_id}/trigger-wave")
def manually_escalate_wave(
    request_id: str,
    current_admin: User = Depends(require_admin),
    db: DatabaseSession = Depends(get_db)
):
    """Allows an administrator to manually trigger the next concentric wave."""
    new_wave = progress_wave(db, request_id)
    if not new_wave:
        return {"status": "EXHAUSTED_OR_COMPLETED", "message": "No additional waves could be triggered."}
    return {
        "status": "WAVE_TRIGGERED",
        "wave_number": new_wave.wave_number,
        "radius_km": new_wave.radius_km,
        "candidates": new_wave.candidate_count
    }

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
