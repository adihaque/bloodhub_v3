import concurrent.futures
from datetime import datetime, timedelta
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from bloodhub.core.config import settings
from bloodhub.core.database import get_db, SessionLocal, DatabaseSession
from bloodhub.core.security import hash_password
from bloodhub.models.models import (
    User, DonorProfile, RequesterProfile, BloodRequest, DispatchWave, DonorOffer,
    Assignment, DonationRecord, BloodCenter, AuditLog
)
from bloodhub.engine.dispatcher import start_dispatch, progress_wave
from bloodhub.engine.concurrency import atomic_accept_offer

router = APIRouter(prefix="/simulator", tags=["Local Multi-User Simulator"])

@router.post("/seed")
def seed_simulator_data(db: DatabaseSession = Depends(get_db), force: bool = False):
    """
    Seeds development/testing data: Donors A/B/C/D, Requester, Admin, and prominent Dhaka blood centers.
    Strictly blocked in 'pilot' (real-user) mode unless explicitly forced, to prevent real database contamination.
    """
    if settings.ENVIRONMENT == "pilot" and not force:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Simulator data seeding is disabled in 'pilot' mode to prevent wiping real donor records. "
                   "Set APP_ENV=development in your .env file to use the test/simulator environment."
        )

    # Clear simulation tables
    db.query(DonationRecord).delete()
    db.query(Assignment).delete()
    db.query(DonorOffer).delete()
    db.query(DispatchWave).delete()
    db.query(BloodRequest).delete()
    db.query(DonorProfile).delete()
    db.query(RequesterProfile).delete()
    db.query(User).delete()
    db.query(BloodCenter).delete()
    db.commit()

    # 1. Admin
    admin = User(
        phone=settings.ADMIN_PHONE,
        email=settings.ADMIN_EMAIL,
        full_name=settings.ADMIN_NAME,
        password_hash=hash_password(settings.ADMIN_PASSWORD),
        role="ADMIN",
        is_verified=1,
        is_active=1
    )
    db.add(admin)

    # 2. Requester
    requester = User(
        phone="+8801711111111",
        email="requester@bloodhub.org.bd",
        full_name="Dr. Farhana Karim",
        password_hash=hash_password("requester123"),
        role="REQUESTER",
        is_verified=1,
        is_active=1
    )
    db.add(requester)
    db.flush()

    db.add(RequesterProfile(user_id=requester.id, alternate_phone="+8801811111111"))

    # 3. Donors
    donors_data = [
        {
            "name": "Donor A (Tanvir Ahmed)",
            "phone": "+8801722222222",
            "whatsapp": "+8801722222222",
            "blood_group": "B+",
            "intent": "REGULAR",
            "area": "Panthapath, Dhaka",
            "lat": 23.7535, "lon": 90.3820,
            "address": "Panthapath, Dhaka (Near Square Hospital)",
            "radius": 10.0,
            "reliability": 0.95
        },
        {
            "name": "Donor B (Sabbir Hossain)",
            "phone": "+8801733333333",
            "whatsapp": "+8801733333333",
            "blood_group": "B+",
            "intent": "WHEN_NEEDED",
            "area": "Dhanmondi, Dhaka",
            "lat": 23.7461, "lon": 90.3742,
            "address": "Dhanmondi 27, Dhaka",
            "radius": 15.0,
            "reliability": 0.88
        },
        {
            "name": "Donor C (Nayeem Islam)",
            "phone": "+8801744444444",
            "whatsapp": "+8801744444444",
            "blood_group": "O+",
            "intent": "REGULAR",
            "area": "Shahbag, Dhaka",
            "lat": 23.7388, "lon": 90.3957,
            "address": "Shahbag, Dhaka (Near BSMMU)",
            "radius": 15.0,
            "reliability": 0.92
        },
        {
            "name": "Donor D (Faruk Hasan)",
            "phone": "+8801755555555",
            "whatsapp": "+8801755555555",
            "blood_group": "B+",
            "intent": "DONATE_LATER",
            "area": "Gulshan, Dhaka",
            "lat": 23.7805, "lon": 90.4267,
            "address": "Gulshan 1, Dhaka (Distant)",
            "radius": 20.0,
            "reliability": 0.80
        }
    ]

    for d in donors_data:
        u = User(
            phone=d["phone"],
            full_name=d["name"],
            password_hash=hash_password("donor123"),
            role="DONOR",
            is_verified=1,
            is_active=1
        )
        db.add(u)
        db.flush()

        prof = DonorProfile(
            user_id=u.id,
            blood_group=d["blood_group"],
            whatsapp_number=d["whatsapp"],
            donation_intent=d["intent"],
            area_district=d["area"],
            date_of_birth="1999-04-12",
            gender="MALE",
            weight_kg=68.0,
            availability_status="AVAILABLE" if d["intent"] != "DONATE_LATER" else "UNAVAILABLE",
            latitude=d["lat"],
            longitude=d["lon"],
            address=d["address"],
            preferred_radius_km=d["radius"],
            last_donation_date="2026-04-10",
            total_donations=3,
            reliability_score=d["reliability"]
        )
        db.add(prof)

    # 4. Verified Blood Centers
    centers = [
        BloodCenter(
            name="Dhaka Medical College Hospital (DMCH) Blood Bank",
            type="HOSPITAL_BANK",
            division="Dhaka",
            district="Dhaka",
            address="Secretariat Rd, Dhaka 1000",
            latitude=23.7258,
            longitude=90.3976,
            phone="+880255165088",
            helpline="16263",
            is_verified=1,
            available_stock_summary="Whole Blood, PRBC available; 24/7 emergency service."
        ),
        BloodCenter(
            name="BSMMU Transfusion Medicine Dept",
            type="HOSPITAL_BANK",
            division="Dhaka",
            district="Dhaka",
            address="Shahbag, Dhaka 1000",
            latitude=23.7388,
            longitude=90.3957,
            phone="+88029661051",
            helpline="16263",
            is_verified=1,
            available_stock_summary="Platelet apheresis, FFP, Cryoprecipitate available."
        ),
        BloodCenter(
            name="Quantum Voluntary Blood Donation Lab",
            type="QUANTUM",
            division="Dhaka",
            district="Dhaka",
            address="31/V Shilpacharya Zainul Abedin Sarak, Shantinagar, Dhaka",
            latitude=23.7371,
            longitude=90.4132,
            phone="+8801714010869",
            helpline="+88029351969",
            is_verified=1,
            available_stock_summary="Screened screened components, 24-hour testing lab."
        ),
        BloodCenter(
            name="Red Crescent Blood Center",
            type="RED_CRESCENT",
            division="Dhaka",
            district="Dhaka",
            address="7/5 Aurangzeb Road, Mohammadpur, Dhaka",
            latitude=23.7601,
            longitude=90.3621,
            phone="+880248121182",
            helpline="+8801711604266",
            is_verified=1,
            available_stock_summary="Humanitarian blood supply, voluntary donation drives."
        ),
        BloodCenter(
            name="Badhan Central Coordination (Dhaka University)",
            type="STUDENT_VOLUNTEER",
            division="Dhaka",
            district="Dhaka",
            address="TSC Ground Floor, University of Dhaka",
            latitude=23.7323,
            longitude=90.3955,
            phone="+8801534982674",
            helpline="01534-982674",
            is_verified=1,
            available_stock_summary="Student voluntary donor mobilization network."
        )
    ]
    for c in centers:
        db.add(c)

    db.commit()
    return {
        "status": "SUCCESS",
        "environment": settings.ENVIRONMENT,
        "message": f"Simulation environment seeded successfully in '{settings.ENVIRONMENT}' mode."
    }

@router.get("/state")
def get_simulator_state(db: DatabaseSession = Depends(get_db)):
    """Returns the current state of all simulated donors, requests, waves, and offers."""
    users = db.query(User).filter_by(role="DONOR").all()
    donor_list = []
    for u in users:
        p = db.query(DonorProfile).filter_by(user_id=u.id).first()
        active_offer = db.query(DonorOffer).filter(
            "donor_id = ? AND status = 'OFFERED'", [u.id]
        ).first()

        donor_list.append({
            "id": u.id,
            "name": u.full_name,
            "phone": u.phone,
            "whatsapp": p.whatsapp_number if p else None,
            "blood_group": p.blood_group if p else "N/A",
            "intent": p.donation_intent if p else "REGULAR",
            "status": p.availability_status if p else "N/A",
            "location": p.area_district or p.address if p else "N/A",
            "active_offer_id": active_offer.id if active_offer else None
        })

    requests = db.query(BloodRequest).order_by("created_at DESC").all()
    req_list = []
    for r in requests:
        assignments = db.query(Assignment).filter_by(request_id=r.id).all()
        waves = db.query(DispatchWave).filter_by(request_id=r.id).all()
        offers = db.query(DonorOffer).filter_by(request_id=r.id).all()

        req_list.append({
            "id": r.id,
            "patient_name": r.patient_name,
            "blood_group": r.blood_group,
            "hospital_name": r.hospital_name,
            "status": r.status,
            "current_wave": r.current_wave,
            "units_needed": r.units_needed,
            "units_fulfilled": r.units_fulfilled,
            "assigned_count": len(assignments),
            "waves_count": len(waves),
            "offers": [
                {
                    "offer_id": o.id,
                    "donor_id": o.donor_id,
                    "status": o.status
                }
                for o in offers
            ]
        })

    return {
        "environment": settings.ENVIRONMENT,
        "donors": donor_list,
        "requests": req_list
    }

@router.post("/trigger-request")
def trigger_test_request(db: DatabaseSession = Depends(get_db)):
    """Creates a sample emergency blood request for B+ at Square Hospital Panthapath."""
    requester = db.query(User).filter_by(role="REQUESTER").first()
    if not requester:
        requester = db.query(User).filter_by(role="ADMIN").first()

    if not requester:
        raise HTTPException(status_code=400, detail="No requester or admin account found.")

    req = BloodRequest(
        requester_id=requester.id,
        patient_name="Anisur Rahman (Emergency Post-Op Bleeding)",
        blood_group="B+",
        component="WHOLE_BLOOD",
        units_needed=1,
        units_fulfilled=0,
        urgency="CRITICAL_IMMEDIATE",
        hospital_name="Square Hospital",
        hospital_address="18/F Bir Uttam Qazi Nuruzzaman Sarak, Panthapath, Dhaka",
        latitude=23.7533,
        longitude=90.3817,
        contact_phone=requester.phone,
        status="ACTIVE"
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    start_dispatch(db, req.id)
    db.refresh(req)

    return {
        "status": "REQUEST_TRIGGERED",
        "request_id": req.id,
        "blood_group": req.blood_group,
        "hospital": req.hospital_name,
        "current_wave": req.current_wave
    }

@router.post("/donor-accept")
def simulate_donor_accept(donor_phone: str, db: DatabaseSession = Depends(get_db)):
    donor = db.query(User).filter_by(phone=donor_phone).first()
    if not donor:
        raise HTTPException(status_code=404, detail="Donor not found")

    offer = db.query(DonorOffer).filter(
        "donor_id = ? AND status = 'OFFERED'", [donor.id]
    ).first()
    if not offer:
        raise HTTPException(status_code=400, detail="No active OFFERED state found for this donor.")

    res = atomic_accept_offer(db, offer_id=offer.id, donor_id=donor.id)
    return res

@router.post("/simultaneous-accept")
def simulate_concurrent_accept_race():
    db = SessionLocal()
    offers = db.query(DonorOffer).filter("status = 'OFFERED'").all()
    if len(offers) < 2:
        db.close()
        raise HTTPException(
            status_code=400,
            detail="Need at least 2 active offers to test concurrency race. Run /simulator/trigger-request first."
        )

    offer_a, offer_b = offers[0], offers[1]
    db.close()

    results = []

    def attempt_accept(offer_id: str, donor_id: str, thread_name: str):
        thread_db = SessionLocal()
        try:
            res = atomic_accept_offer(thread_db, offer_id, donor_id)
            res["thread"] = thread_name
            res["donor_id"] = donor_id
            results.append(res)
        finally:
            thread_db.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(attempt_accept, offer_a.id, offer_a.donor_id, "Thread-Donor-1")
        f2 = executor.submit(attempt_accept, offer_b.id, offer_b.donor_id, "Thread-Donor-2")
        concurrent.futures.wait([f1, f2])

    winners = [r for r in results if r.get("success") is True]
    losers = [r for r in results if r.get("success") is False]

    return {
        "test_status": "CONCURRENCY_TEST_COMPLETE",
        "total_attempts": len(results),
        "winners_count": len(winners),
        "losers_count": len(losers),
        "winner_details": winners[0] if winners else None,
        "loser_details": losers[0] if losers else None,
        "guarantee_verified": (len(winners) == 1 and len(losers) == 1)
    }

@router.post("/wave-timeout")
def simulate_wave_timeout(request_id: str, db: DatabaseSession = Depends(get_db)):
    new_wave = progress_wave(db, request_id)
    if not new_wave:
        return {"status": "NO_MORE_WAVES_OR_COMPLETED"}
    return {
        "status": "WAVE_ESCALATED",
        "wave_number": new_wave.wave_number,
        "radius_km": new_wave.radius_km,
        "candidates_targeted": new_wave.candidate_count
    }
