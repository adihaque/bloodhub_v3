# Blood Hub: System Architecture & Technical Specification

## 1. System Overview

Blood Hub is a blood-donation emergency coordination platform organized around a **Modular Monolith** architecture with ride-hailing dispatch semantics.

### Architecture Diagram
```
+-------------------------------------------------------------------------+
|                           CLIENT SURFACES                               |
|   Requester Web Portal  │  Donor Mobile PWA  │  Admin & Simulator UI    |
+------------------------------------+------------------------------------+
                                     │ HTTP / SSE
                                     v
+-------------------------------------------------------------------------+
|                        FASTAPI APPLICATION CORE                         |
|   Auth & RBAC Middleware  │  Pydantic Schemas  │  Static Asset Serving  |
+------------------------------------+------------------------------------+
                                     │
       ┌─────────────────────────────┼─────────────────────────────┐
       v                             v                             v
+───────────────+             +───────────────+             +─────────────+
| DOMAIN LAYER  |             | DISPATCH CORE |             | CONCURRENCY |
| Compatibility |             | Wave Sched.   |             | Atomic Lock |
| Eligibility   |             | Ranking Eng.  |             | Row Mutex   |
| Geospatial    |             | Offer Manager |             | Revocation  |
+───────┬───────+             +───────┬───────+             +──────┬──────+
        │                             │                            │
        └─────────────────────────────┼────────────────────────────┘
                                      v
+-------------------------------------------------------------------------+
|                        PERSISTENCE & REPOSITORIES                       |
|          SQLite 3 (WAL mode + Haversine) / PostgreSQL + PostGIS         |
+-------------------------------------------------------------------------+
                                      ^
                                      │ Authoritative Sweep (every 5s)
+-------------------------------------+-----------------------------------+
|                       BACKGROUND TASK WORKER                            |
|             Wave Timeouts  │  Offer Reconciliation  │  Purging          |
+-------------------------------------------------------------------------+
```

---

## 2. Core Architectural Pillars

1. **Medical Boundary Isolation**: Platform eligibility rules (age, weight, donation interval) are isolated behind `bloodhub.domain.eligibility` and clearly designated as logistical filters rather than medical clearance.
2. **Authoritative Concurrency**: Donor acceptance operations serialize on request records. Only one donor can claim an active unit.
3. **Open-Source & Self-Hostable**: Built with standard Python 3.11, FastAPI, and SQLite/PostgreSQL with zero mandatory paid SaaS dependencies.
