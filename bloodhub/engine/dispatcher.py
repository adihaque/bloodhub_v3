import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from bloodhub.core.database import DatabaseSession
from bloodhub.models.models import (
    BloodRequest, DispatchWave, DonorOffer, DonorProfile, User, BloodCenter, AuditLog, AlgorithmConfig
)
from bloodhub.domain.compatibility import get_compatible_donor_groups
from bloodhub.domain.eligibility import check_donor_eligibility
from bloodhub.domain.geospatial import haversine_distance
from bloodhub.domain.ranking import calculate_candidate_score
from bloodhub.domain.state_machines import RequestStateMachine, DonorStateMachine
from bloodhub.core.config import settings
from bloodhub.providers.notifications.console import MultiChannelNotificationProvider

notification_provider = MultiChannelNotificationProvider()

def get_active_algorithm_config(db: DatabaseSession) -> AlgorithmConfig:
    """Retrieves dynamic algorithm configuration from the database or returns defaults."""
    cfg = db.query(AlgorithmConfig).filter_by(id="active_config").first()
    if not cfg:
        cfg = AlgorithmConfig(
            id="active_config",
            compatibility_exact_pts=40.0,
            compatibility_compatible_pts=25.0,
            proximity_weight_pts=35.0,
            reliability_weight_pts=15.0,
            interval_weight_pts=10.0,
            intent_regular_bonus=5.0,
            intent_when_needed_bonus=2.0,
            cooldown_days=90,
            wave1_radius_km=5.0,
            wave1_timeout_sec=25,
            wave1_candidates=4,
            wave2_radius_km=8.0,
            wave2_timeout_sec=25,
            wave2_candidates=6,
            wave3_radius_km=15.0,
            wave3_timeout_sec=30,
            wave3_candidates=10,
            wave4_radius_km=25.0,
            wave4_timeout_sec=35,
            wave4_candidates=15,
            auto_dispatch_whatsapp=1,
            auto_dispatch_in_app=1,
            auto_dispatch_sms=1
        )
    return cfg

def get_wave_specs_from_config(cfg: AlgorithmConfig) -> List[Dict[str, Any]]:
    """Constructs dynamic 4-wave dispatch specifications from algorithm config."""
    return [
        {
            "wave_number": 1,
            "radius_km": float(cfg.wave1_radius_km or 5.0),
            "candidate_count": int(cfg.wave1_candidates or 4),
            "timeout_seconds": int(cfg.wave1_timeout_sec or 25)
        },
        {
            "wave_number": 2,
            "radius_km": float(cfg.wave2_radius_km or 8.0),
            "candidate_count": int(cfg.wave2_candidates or 6),
            "timeout_seconds": int(cfg.wave2_timeout_sec or 25)
        },
        {
            "wave_number": 3,
            "radius_km": float(cfg.wave3_radius_km or 15.0),
            "candidate_count": int(cfg.wave3_candidates or 10),
            "timeout_seconds": int(cfg.wave3_timeout_sec or 30)
        },
        {
            "wave_number": 4,
            "radius_km": float(cfg.wave4_radius_km or 25.0),
            "candidate_count": int(cfg.wave4_candidates or 15),
            "timeout_seconds": int(cfg.wave4_timeout_sec or 35)
        }
    ]

def find_and_rank_candidates(
    db: DatabaseSession,
    request: BloodRequest,
    radius_km: float,
    max_count: int,
    exclude_donor_ids: Optional[List[str]] = None,
    config: Optional[AlgorithmConfig] = None
) -> List[Dict[str, Any]]:
    """
    Finds compatible, eligible donors within radius and deterministically ranks them
    using active algorithm weights.
    """
    if config is None:
        config = get_active_algorithm_config(db)

    exclude_ids = set(exclude_donor_ids or [])
    compatible_groups = get_compatible_donor_groups(request.blood_group, request.component)

    if not compatible_groups:
        return []

    placeholders = ", ".join(["?"] * len(compatible_groups))
    sql_filter = f"blood_group IN ({placeholders}) AND availability_status = 'AVAILABLE'"
    profiles = db.query(DonorProfile).filter(sql_filter, compatible_groups).all()

    candidates = []
    for profile in profiles:
        if profile.user_id in exclude_ids or profile.user_id == request.requester_id:
            continue

        user = db.query(User).filter_by(id=profile.user_id, is_active=1).first()
        if not user:
            continue

        # 1. Eligibility Check
        eligible, reason = check_donor_eligibility(
            availability_status=profile.availability_status,
            weight_kg=profile.weight_kg,
            birth_date_str=profile.date_of_birth,
            last_donation_date_str=profile.last_donation_date,
            gender=profile.gender,
            component=request.component,
            active_assignment_id=profile.active_assignment_id
        )
        if not eligible:
            continue

        # 2. Distance Calculation
        dist_km = haversine_distance(
            request.latitude, request.longitude,
            profile.latitude, profile.longitude
        )

        if dist_km > radius_km:
            continue

        # Respect donor's preferred maximum radius if specified
        pref_radius = float(profile.preferred_radius_km or 25.0)
        if dist_km > pref_radius:
            continue

        # 3. Deterministic Ranking with Active Config
        score_info = calculate_candidate_score(
            donor_blood_group=profile.blood_group,
            recipient_blood_group=request.blood_group,
            distance_km=dist_km,
            max_radius_km=radius_km,
            reliability_score=profile.reliability_score,
            last_donation_date_str=profile.last_donation_date,
            donation_intent=profile.donation_intent or "REGULAR",
            config=config
        )

        candidates.append({
            "donor_id": user.id,
            "user": user,
            "profile": profile,
            "distance_km": dist_km,
            "score": score_info["total_score"],
            "score_breakdown": score_info["breakdown"]
        })

    # Sort descending by score, then ascending by distance
    candidates.sort(key=lambda c: (-c["score"], c["distance_km"]))
    return candidates[:max_count]

def start_dispatch(db: DatabaseSession, request_id: str) -> Optional[DispatchWave]:
    """
    Initializes the wave dispatch engine for a blood request using active algorithm configuration.
    """
    request = db.query(BloodRequest).filter_by(id=request_id).first()
    if not request:
        return None

    algo_cfg = get_active_algorithm_config(db)
    wave_specs = get_wave_specs_from_config(algo_cfg)

    # Validate transition to MATCHING
    RequestStateMachine.validate_transition(request.status, "MATCHING")
    request.status = "MATCHING"
    request.current_wave = 1

    wave_config = wave_specs[0]
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=wave_config["timeout_seconds"])

    wave = DispatchWave(
        request_id=request.id,
        wave_number=1,
        radius_km=wave_config["radius_km"],
        candidate_count=0,
        timeout_seconds=wave_config["timeout_seconds"],
        status="ACTIVE",
        started_at=now.isoformat(),
        expires_at=expires_at.isoformat()
    )
    db.add(wave)
    db.flush()

    candidates = find_and_rank_candidates(
        db, request,
        radius_km=wave.radius_km,
        max_count=wave_config["candidate_count"],
        config=algo_cfg
    )

    wave.candidate_count = len(candidates)
    db.add(wave)

    if candidates:
        RequestStateMachine.validate_transition(request.status, "AWAITING_DONOR")
        request.status = "AWAITING_DONOR"

        for cand in candidates:
            profile = cand["profile"]
            user = cand["user"]
            DonorStateMachine.validate_transition(profile.availability_status, "OFFERED")
            profile.availability_status = "OFFERED"
            profile.response_count = int(profile.response_count or 0) + 1
            db.add(profile)

            offer = DonorOffer(
                wave_id=wave.id,
                request_id=request.id,
                donor_id=cand["donor_id"],
                status="OFFERED",
                channels="IN_APP,WHATSAPP,SMS",
                score=cand["score"],
                distance_km=cand["distance_km"],
                score_breakdown=json.dumps(cand["score_breakdown"]),
                sent_at=now.isoformat(),
                expires_at=expires_at.isoformat()
            )
            db.add(offer)
            db.flush()

            # Multi-channel notification delivery (In-App, WhatsApp deep link, SMS)
            notify_res = notification_provider.send_dispatch_offer(
                cand["donor_id"],
                {
                    "offer_id": offer.id,
                    "blood_group": request.blood_group,
                    "component": request.component,
                    "hospital_name": request.hospital_name,
                    "hospital_address": request.hospital_address,
                    "patient_name": request.patient_name,
                    "distance_km": cand["distance_km"],
                    "timeout_seconds": wave_config["timeout_seconds"],
                    "donor_name": user.full_name,
                    "donor_phone": user.phone,
                    "whatsapp_number": profile.whatsapp_number
                }
            )

            offer.whatsapp_url = notify_res.get("whatsapp_url")
            db.add(offer)

    else:
        # If no candidates in Wave 1, attempt immediate progression to Wave 2
        db.commit()
        return progress_wave(db, request.id)

    db.add(request)
    db.commit()
    db.refresh(wave)
    return wave

def progress_wave(db: DatabaseSession, request_id: str) -> Optional[DispatchWave]:
    """
    Escalates dispatch to the next wave when previous wave times out or yields no acceptance.
    """
    request = db.query(BloodRequest).filter_by(id=request_id).first()
    if not request or request.status in ("ASSIGNED", "CONFIRMED", "COMPLETED", "CANCELLED", "EXPIRED"):
        return None

    algo_cfg = get_active_algorithm_config(db)
    wave_specs = get_wave_specs_from_config(algo_cfg)

    # Expire previous active offers and waves
    active_waves = db.query(DispatchWave).filter(
        "request_id = ? AND status = 'ACTIVE'", [request.id]
    ).all()

    for w in active_waves:
        w.status = "TIMED_OUT"
        db.add(w)
        offers = db.query(DonorOffer).filter(
            "wave_id = ? AND status = 'OFFERED'", [w.id]
        ).all()
        for off in offers:
            off.status = "TIMED_OUT"
            db.add(off)
            donor_prof = db.query(DonorProfile).filter_by(user_id=off.donor_id).first()
            if donor_prof and donor_prof.availability_status == "OFFERED":
                donor_prof.availability_status = "AVAILABLE"
                donor_prof.timeout_count = int(donor_prof.timeout_count or 0) + 1
                db.add(donor_prof)

    next_wave_num = request.current_wave + 1
    if next_wave_num > len(wave_specs):
        # All waves exhausted
        request.status = "UNFULFILLED"
        audit = AuditLog(
            action="DISPATCH_EXHAUSTED",
            resource_type="BloodRequest",
            resource_id=request.id,
            details=f"All {len(wave_specs)} waves exhausted without acceptance."
        )
        db.add(audit)
        db.add(request)
        db.commit()
        return None

    request.current_wave = next_wave_num
    request.status = "MATCHING"
    wave_config = wave_specs[next_wave_num - 1]

    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=wave_config["timeout_seconds"])

    new_wave = DispatchWave(
        request_id=request.id,
        wave_number=next_wave_num,
        radius_km=wave_config["radius_km"],
        candidate_count=0,
        timeout_seconds=wave_config["timeout_seconds"],
        status="ACTIVE",
        started_at=now.isoformat(),
        expires_at=expires_at.isoformat()
    )
    db.add(new_wave)
    db.flush()

    # Get IDs of donors previously offered in this request
    previously_offered = [
        o.donor_id for o in db.query(DonorOffer).filter_by(request_id=request.id).all()
    ]

    candidates = find_and_rank_candidates(
        db, request,
        radius_km=new_wave.radius_km,
        max_count=wave_config["candidate_count"],
        exclude_donor_ids=previously_offered,
        config=algo_cfg
    )

    new_wave.candidate_count = len(candidates)
    db.add(new_wave)

    if candidates:
        request.status = "AWAITING_DONOR"
        for cand in candidates:
            profile = cand["profile"]
            user = cand["user"]
            profile.availability_status = "OFFERED"
            profile.response_count = int(profile.response_count or 0) + 1
            db.add(profile)

            offer = DonorOffer(
                wave_id=new_wave.id,
                request_id=request.id,
                donor_id=cand["donor_id"],
                status="OFFERED",
                channels="IN_APP,WHATSAPP,SMS",
                score=cand["score"],
                distance_km=cand["distance_km"],
                score_breakdown=json.dumps(cand["score_breakdown"]),
                sent_at=now.isoformat(),
                expires_at=expires_at.isoformat()
            )
            db.add(offer)
            db.flush()

            notify_res = notification_provider.send_dispatch_offer(
                cand["donor_id"],
                {
                    "offer_id": offer.id,
                    "blood_group": request.blood_group,
                    "component": request.component,
                    "hospital_name": request.hospital_name,
                    "hospital_address": request.hospital_address,
                    "patient_name": request.patient_name,
                    "distance_km": cand["distance_km"],
                    "timeout_seconds": wave_config["timeout_seconds"],
                    "donor_name": user.full_name,
                    "donor_phone": user.phone,
                    "whatsapp_number": profile.whatsapp_number
                }
            )
            offer.whatsapp_url = notify_res.get("whatsapp_url")
            db.add(offer)
    else:
        db.add(request)
        db.commit()
        if next_wave_num < len(wave_specs):
            return progress_wave(db, request.id)
        else:
            request.status = "UNFULFILLED"

    db.add(request)
    db.commit()
    db.refresh(new_wave)
    return new_wave
