# Blood Hub: Third-Party Service Inventory & Cost Analysis

This document evaluates all external dependencies, third-party software services, and cloud integrations for Blood Hub.

---

## 1. Master Service Inventory Table

| Service Category | Recommended Provider | Purpose | Required? | Free Tier | Est. Cost (1k req/mo) | Est. Cost (10k req/mo) | Est. Cost (100k req/mo) | Self-Hostable Alternative | Migration Effort |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SMS Gateway (Domestic)** | SSL Wireless / Greenweb BD | OTP verification & urgent SMS alerts | **Yes (Prod)** | None (Trial credits) | ~$3.50 (BDT 400) | ~$35.00 (BDT 4,000) | ~$300.00 (BDT 35,000) | Kannel / Gammu GSM Modem | Low (Abstract `SmsProvider`) |
| **Push Notifications** | Firebase Cloud Messaging (FCM) / WebPush | Urgent incoming call-like prompts & wave alerts | **Yes (Prod)** | Unlimited free messages | $0.00 | $0.00 | $0.00 | Gotify / Direct WebPush VAPID | Medium |
| **Geocoding & Maps** | OpenStreetMap / Leaflet (Built-in) | Coordinate calculation & hospital mapping | **Yes** | Built-in / Free OSM | $0.00 | $0.00 | $0.00 | Self-hosted Nominatim / OSRM | Low (Abstract `MapProvider`) |
| **Routing / Distance** | Geodesic Haversine (Built-in) | Distance computation in PostGIS / SQLite | **Yes** | Built-in | $0.00 | $0.00 | $0.00 | OSRM / Valhalla Docker | Low |
| **Database** | PostgreSQL / SQLite | Data persistence & transaction locking | **Yes** | Open source / Free | $0.00 (Local/VPS) | $15.00 (Cloud VPS) | $40.00 (Managed RDS/DO) | PostgreSQL native | None |

---

## 2. Detailed Service Evaluation

### 2.1 SMS Gateway (SSL Wireless / Greenweb BD)
- **Purpose**: Authenticating phone numbers via one-time passwords (OTP) during registration and delivering backup SMS notifications when mobile data is turned off.
- **Required**: Yes for production phone verification in Bangladesh. In development, defaults to `MockSmsProvider` (prints to console).
- **Cost**: Approximately BDT 0.35 - 0.40 per SMS.
- **Self-Hostable Alternative**: Hardware GSM modem with SIM pool. Not recommended due to BTRC regulatory restrictions on commercial bulk messaging.
- **Failure Impact**: Registration and SMS fallback delayed. Core push/web dispatch continues.

### 2.2 Push Notifications (FCM / WebPush)
- **Purpose**: High-priority alert delivery to mobile devices to trigger the emergency call prompt.
- **Required**: Yes for native mobile background waking.
- **Cost**: Free tier covers standard messaging.
- **Self-Hostable Alternative**: WebPush with local VAPID keys.

### 2.3 Maps & Routing (OpenStreetMap & Haversine)
- **Purpose**: Hospital proximity matching and donor distance estimation.
- **Required**: Yes. Integrated directly into the platform codebase via `bloodhub.domain.geospatial` and `OpenStreetMapProvider`.
- **Cost**: $0.00. Zero external API bills.
