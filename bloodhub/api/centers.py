from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from bloodhub.core.database import get_db, DatabaseSession
from bloodhub.models.models import BloodCenter, User
from bloodhub.schemas.schemas import BloodCenterOut, BloodCenterCreate
from bloodhub.api.deps import require_admin
from bloodhub.domain.geospatial import haversine_distance

router = APIRouter(prefix="/centers", tags=["Blood Centers & Banks"])

@router.get("/", response_model=List[BloodCenterOut])
def list_blood_centers(
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    division: Optional[str] = Query(None),
    db: DatabaseSession = Depends(get_db)
):
    builder = db.query(BloodCenter).filter("is_verified = 1")
    if division:
        builder.filter("division = ?", [division])

    centers = builder.all()
    results = []
    for c in centers:
        dist = None
        if lat is not None and lon is not None:
            dist = haversine_distance(lat, lon, c.latitude, c.longitude)
        
        c_dict = c.to_dict()
        c_dict["distance_km"] = dist
        results.append(c_dict)

    if lat is not None and lon is not None:
        results.sort(key=lambda x: (x["distance_km"] if x["distance_km"] is not None else 9999))

    return results

@router.post("/", response_model=BloodCenterOut)
def create_blood_center(
    payload: BloodCenterCreate,
    current_admin: User = Depends(require_admin),
    db: DatabaseSession = Depends(get_db)
):
    center = BloodCenter(
        name=payload.name.strip(),
        type=payload.type,
        division=payload.division,
        district=payload.district,
        address=payload.address.strip(),
        latitude=payload.latitude,
        longitude=payload.longitude,
        phone=payload.phone.strip(),
        helpline=payload.helpline,
        is_verified=1,
        available_stock_summary=payload.available_stock_summary
    )
    db.add(center)
    db.commit()
    db.refresh(center)
    return center.to_dict()
