import asyncio
import json
from datetime import datetime
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from bloodhub.core.database import SessionLocal
from bloodhub.models.models import BloodRequest, DispatchWave, DonorOffer

router = APIRouter(prefix="/events", tags=["Realtime Events"])

async def event_generator():
    """Streams real-time updates to connected clients using Server-Sent Events (SSE)."""
    while True:
        try:
            db = SessionLocal()
            active_reqs = db.query(BloodRequest).filter(
                BloodRequest.status.in_(["MATCHING", "AWAITING_DONOR", "ACTIVE"])
            ).count()
            active_waves = db.query(DispatchWave).filter(DispatchWave.status == "ACTIVE").count()
            active_offers = db.query(DonorOffer).filter(DonorOffer.status == "OFFERED").count()
            db.close()

            payload = {
                "timestamp": datetime.utcnow().isoformat(),
                "active_requests": active_reqs,
                "active_waves": active_waves,
                "active_offers": active_offers
            }
            yield f"event: ping\ndata: {json.dumps(payload)}\n\n"
        except Exception:
            pass

        await asyncio.sleep(3)

@router.get("/stream")
def sse_event_stream():
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
