# 🩸 Blood Hub

> **Autonomous Blood Donation Coordination Platform (Ride-Hailing Dispatch Model)**  
> Built for Bangladesh with low-bandwidth optimization, deterministic geospatial matching, concentric wave dispatch, and atomic concurrency protection.

---

## 🚑 The Problem & The Solution

In medical crises across Bangladesh (postpartum hemorrhage, dengue platelet crashes, road traffic trauma), sourcing emergency blood currently relies on frantic social media posts or broadcast flood messages. This causes donor alert fatigue, duplicate travel, and delays.

**Blood Hub transforms blood coordination into a dispatch model:**
1. A requester enters the patient's blood group, urgency, and hospital location.
2. The engine filters medically compatible donors, verifies donation cooldown intervals, and ranks candidates deterministically.
3. Requests are dispatched in **concentric waves** (Wave 1: 5km $\rightarrow$ Wave 2: 8km $\rightarrow$ Wave 3: 15km $\rightarrow$ Wave 4: 25km).
4. Matched donors receive an **urgent incoming call-style screen** with audio chime and countdown timer.
5. When a donor accepts, **atomic row-level database locking** guarantees strictly ONE winner.
6. If volunteer waves time out, the system automatically transitions to verified institutional blood banks (Red Crescent, Quantum, DMCH).

---

## 🏗️ Architecture & Technology Stack

- **Backend**: Python 3.11 + FastAPI (Modular Monolith)
- **Database**: Relational SQLite 3 (WAL mode with custom C/Python Haversine distance functions) / PostgreSQL + PostGIS
- **Concurrency**: Database transaction row locking ensuring zero race-condition over-allocation
- **Worker**: Authoritative server-side background task scheduler for wave timeouts and expirations
- **Frontend**: Lightweight mobile-first responsive PWA + Web Audio API alert synthesizer
- **Maps**: OpenStreetMap and geodesic Haversine distance (zero external API licensing costs)
- **Localization**: Bangladesh-first (English and Bangla localization support)

---

## ⚡ Quick Start

### 1. Clone & Setup
```bash
# Run tests
python3 -m unittest discover -s tests

# Seed realistic Bangladesh test data
python3 scripts/seed_data.py

# Launch server
uvicorn bloodhub.main:app --host 0.0.0.0 --port 8000
```

### 2. User & Admin Surfaces
- **Landing Page**: [http://localhost:8000/](http://localhost:8000/)
- **Donor Mobile Web App**: [http://localhost:8000/donor](http://localhost:8000/donor)
- **Requester Portal**: [http://localhost:8000/requester](http://localhost:8000/requester)
- **Admin Dashboard**: [http://localhost:8000/admin](http://localhost:8000/admin)
- **Interactive Simulator**: [http://localhost:8000/simulator](http://localhost:8000/simulator)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧪 Local Testing & Simulation

Blood Hub includes a complete multi-user simulation suite:
```bash
python3 scripts/run_simulator.py
```
Or open [http://localhost:8000/simulator](http://localhost:8000/simulator) to visually simulate:
- Donor accepts offer
- Donor declines offer
- Wave timeout and automatic escalation
- **Simultaneous acceptance race condition test (validating atomic concurrency protection)**

---

## 📚 Project Documentation

- **[BEFORE_PRODUCTION.md](BEFORE_PRODUCTION.md)**: Critical pre-launch handover guide for the non-technical owner.
- **[OWNER_GUIDE.md](OWNER_GUIDE.md)**: Plain-language operational manual.
- **[ARCHITECTURE.md](ARCHITECTURE.md)**: Complete system design and modular monolith boundaries.
- **[DISPATCH.md](DISPATCH.md)**: Wave dispatch algorithms and ranking formulas.
- **[DATABASE.md](DATABASE.md)**: Entity-relationship schema and table specifications.
- **[API.md](API.md)**: REST API endpoints and payload specifications.
- **[SECURITY.md](SECURITY.md)**: Threat model and security controls.
- **[OPERATIONS.md](OPERATIONS.md)**: Monitoring, backups, and disaster recovery.
- **[SERVICES.md](SERVICES.md)**: Third-party service inventory and cost analysis.
- **[DECISIONS.md](DECISIONS.md)**: Architecture Decision Records (ADRs).
- **[DEVELOPMENT.md](DEVELOPMENT.md)**: Local developer setup.
- **[TESTING.md](TESTING.md)**: Automated test execution guide.
- **[DEPLOYMENT.md](DEPLOYMENT.md)**: Production deployment instructions.

---

## ⚖️ Medical & Legal Disclaimer

Blood Hub is a logistical coordination platform, NOT a medical clearance or diagnostic system. All blood products must undergo clinical screening for the mandatory 5 TTIs (HIV, HBV, HCV, Syphilis, Malaria) and physical cross-matching by authorized medical personnel under the Safe Blood Transfusion Act 2002.
