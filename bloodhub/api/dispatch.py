from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from bloodhub.core.database import get_db, DatabaseSession
from bloodhub.models.models import BloodRequest, DispatchWave, DonorOffer
from bloodhub.engine.dispatcher import progress_wave

router = APIRouter(prefix="/dispatch", tags=["Dispatch Engine"])

@router.get("/status/{request_id}")
def get_dispatch_status(request_id: str, db: DatabaseSession = Depends(get_db)):
    request = db.query(BloodRequest).filter_by(id=request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Blood request not found")

    waves = db.query(DispatchWave).filter_by(request_id=request.id).order_by("wave_number ASC").all()

    now = datetime.utcnow()
    wave_data = []
    for w in waves:
        offers = db.query(DonorOffer).filter_by(wave_id=w.id).all()
        accepted = sum(1 for o in offers if o.status == "ACCEPTED")
        rejected = sum(1 for o in offers if o.status == "REJECTED")
        timed_out = sum(1 for o in offers if o.status == "TIMED_OUT")
        offered = sum(1 for o in offers if o.status == "OFFERED")
        
        exp_dt = datetime.fromisoformat(w.expires_at) if isinstance(w.expires_at, str) else w.expires_at
        seconds_left = max(0, int((exp_dt - now).total_seconds())) if w.status == "ACTIVE" else 0

        wave_data.append({
            "wave_number": w.wave_number,
            "radius_km": w.radius_km,
            "candidate_count": w.candidate_count,
            "status": w.status,
            "seconds_remaining": seconds_left,
            "offers_offered": offered,
            "offers_accepted": accepted,
            "offers_rejected": rejected,
            "offers_timed_out": timed_out
        })

    return {
        "request_id": request.id,
        "request_status": request.status,
        "blood_group": request.blood_group,
        "units_needed": request.units_needed,
        "units_fulfilled": request.units_fulfilled,
        "current_wave": request.current_wave,
        "waves": wave_data
    }

@router.post("/progress/{request_id}")
def manual_progress_wave(request_id: str, db: DatabaseSession = Depends(get_db)):
    new_wave = progress_wave(db, request_id)
    if not new_wave:
        return {"status": "NO_MORE_WAVES_OR_COMPLETED", "message": "No new wave generated."}
    return {
        "status": "WAVE_PROGRESSED",
        "wave_number": new_wave.wave_number,
        "radius_km": new_wave.radius_km,
        "candidates": new_wave.candidate_count
    }
