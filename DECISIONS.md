# Blood Hub: Architecture Decision Records (ADR)

This document tracks all fundamental architectural decisions made in Blood Hub.

---

### ADR 001: Modular Monolith vs. Microservices
- **Status**: Accepted
- **Decision**: Deploy Blood Hub as a **Modular Monolith** in Python (FastAPI).
- **Rationale**: Blood donation matching involves strict ACID row-level locking during the simultaneous claiming window. Splitting the matching engine, database, and notification pipeline across microservices introduces distributed lock complexity (2PC / Saga patterns) and increases operational maintenance cost for an inexperienced owner. A modular monolith guarantees strict local transaction serialization.

---

### ADR 002: Dual-Engine Database Architecture (PostgreSQL for Prod, SQLite for Dev/Testing)
- **Status**: Accepted
- **Decision**: Support zero-config local SQLite with custom C/Python Haversine trigonometric functions for local development and unit tests, while supporting PostgreSQL + PostGIS for production.
- **Rationale**: New contributors and local operators can clone and immediately run tests in sub-second intervals without setting up complex external databases.

---

### ADR 003: Concentric Wave Dispatch vs. Broadcast Flood
- **Status**: Accepted
- **Decision**: Dispatch offers in sequential concentric waves (Wave 1: 5km, Wave 2: 8km, Wave 3: 15km, Wave 4: 25km) with timeouts.
- **Rationale**: Mass broadcast flooding wakes up hundreds of donors simultaneously, creates alert fatigue, and leads to multiple donors traveling concurrently for a single bag of blood. Concentric waves prioritize immediate neighbors first.

---

### ADR 004: Server-Side Authoritative Concurrency via SELECT FOR UPDATE / Mutex
- **Status**: Accepted
- **Decision**: Enforce atomic state transitions on `BloodRequest` and `DonorOffer` at the database level.
- **Rationale**: When multiple donors click Accept within milliseconds, the server atomically serializes the requests. Only the first donor acquires the lock; subsequent donors receive an immediate notice that the request has been fulfilled. No duplicate assignments can be created.

---

### ADR 005: OpenStreetMap & Leaflet vs. Commercial Maps
- **Status**: Accepted
- **Decision**: Use OpenStreetMap and mathematical geodesic distance calculations.
- **Rationale**: Eliminates expensive per-request API costs (e.g. Google Maps Platform fees) and provides high reliability and privacy within Bangladesh.

---

### ADR 006: Server-Sent Events (SSE) for Real-Time Dispatch Streaming
- **Status**: Accepted
- **Decision**: Use unidirectional Server-Sent Events (`/api/v1/events/stream`) over HTTP/2.
- **Rationale**: SSE works natively over HTTP, traverses hospital firewalls and cellular NAT proxies cleanly, and features built-in browser reconnection protocols without WebSocket handshake overhead.
