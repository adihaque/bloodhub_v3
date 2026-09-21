import time
import logging
from datetime import datetime, timedelta
from bloodhub.core.database import SessionLocal, DatabaseSession
from bloodhub.models.models import BloodRequest, DispatchWave, DonorOffer, DonorProfile, Assignment, AuditLog
from bloodhub.engine.dispatcher import progress_wave

logger = logging.getLogger("bloodhub.worker")

def process_expired_waves(db: DatabaseSession) -> int:
    """Checks for active waves whose timeout window has expired and advances them."""
    now = datetime.utcnow().isoformat()
    expired_waves = db.query(DispatchWave).filter(
        "status = 'ACTIVE' AND expires_at < ?", [now]
    ).all()

    count = 0
    for wave in expired_waves:
        request = db.query(BloodRequest).filter_by(id=wave.request_id).first()
        if request and request.status in ("MATCHING", "AWAITING_DONOR") and int(request.units_fulfilled) < int(request.units_needed):
            logger.info(f"Escalating request {request.id} from wave {wave.wave_number} due to timeout.")
            progress_wave(db, request.id)
            count += 1
        else:
            wave.status = "TIMED_OUT"
            db.add(wave)
            db.commit()

    return count

def process_expired_offers(db: DatabaseSession) -> int:
    """Reconciles orphaned or timed-out offers and frees donor availability."""
    now = datetime.utcnow().isoformat()
    stale_offers = db.query(DonorOffer).filter(
        "status = 'OFFERED' AND expires_at < ?", [now]
    ).all()

    count = 0
    for offer in stale_offers:
        offer.status = "TIMED_OUT"
        db.add(offer)
        donor_prof = db.query(DonorProfile).filter_by(user_id=offer.donor_id).first()
        if donor_prof and donor_prof.availability_status == "OFFERED":
            donor_prof.availability_status = "AVAILABLE"
            donor_prof.timeout_count = int(donor_prof.timeout_count) + 1
            db.add(donor_prof)
        count += 1

    if count > 0:
        db.commit()
    return count

def process_expired_requests(db: DatabaseSession) -> int:
    """Marks unfulfilled requests older than 24 hours as EXPIRED."""
    now = datetime.utcnow()
    cutoff_24h = (now - timedelta(hours=24)).isoformat()
    
    expired_reqs = db.query(BloodRequest).filter(
        "status IN ('MATCHING', 'AWAITING_DONOR', 'ACTIVE', 'DRAFT') AND created_at < ?",
        [cutoff_24h]
    ).all()

    count = 0
    for req in expired_reqs:
        req.status = "EXPIRED"
        db.add(req)
        count += 1

    if count > 0:
        db.commit()
    return count

def run_worker_cycle():
    """Runs a single authoritative maintenance sweep across the platform."""
    db = SessionLocal()
    try:
        w_count = process_expired_waves(db)
        o_count = process_expired_offers(db)
        r_count = process_expired_requests(db)
        return {"waves_progressed": w_count, "offers_reconciled": o_count, "requests_expired": r_count}
    except Exception as e:
        logger.error(f"Worker cycle failed: {e}")
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()

def run_worker_daemon(poll_interval_seconds: int = 5):
    """Authoritative background worker loop."""
    logger.info(f"Starting Blood Hub background worker (polling every {poll_interval_seconds}s)...")
    while True:
        run_worker_cycle()
        time.sleep(poll_interval_seconds)
