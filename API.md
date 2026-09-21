# Blood Hub: REST API Reference Manual

Base URL: `/api/v1`  
Protocol: `HTTP/HTTPS`  
Data Format: `JSON`

---

## 1. Authentication Endpoints

### `POST /api/v1/auth/register`
Register a new donor or requester.
```json
{
  "phone": "+8801722222222",
  "password": "donor123",
  "full_name": "Tanvir Ahmed",
  "role": "DONOR",
  "blood_group": "B+",
  "latitude": 23.7535,
  "longitude": 90.3820,
  "address": "Panthapath, Dhaka"
}
```
Response: `201 Created`
```json
{
  "access_token": "eyJ...",
  "token_type": "Bearer",
  "user": { "id": "...", "phone": "+8801722222222", "full_name": "Tanvir Ahmed", "role": "DONOR" }
}
```

### `POST /api/v1/auth/login`
Authenticate user with phone and password.
```json
{ "phone": "+8801722222222", "password": "donor123" }
```

### `GET /api/v1/auth/me`
Returns current authenticated user details. Requires `Authorization: Bearer <token>`.

---

## 2. Donor Endpoints

### `GET /api/v1/donors/profile`
Returns donor's profile, availability, donation history, and metrics.

### `PUT /api/v1/donors/availability`
Update donor availability status (`AVAILABLE` or `UNAVAILABLE`).
```json
{ "availability_status": "AVAILABLE" }
```

### `PUT /api/v1/donors/location`
Updates donor coordinates for geographic matching.
```json
{ "latitude": 23.7535, "longitude": 90.3820, "address": "Panthapath, Dhaka" }
```

### `GET /api/v1/donors/offers`
Lists pending dispatch offers for the calling donor with countdown seconds, distance, and hospital info.

### `POST /api/v1/donors/offers/{offer_id}/accept`
Atomically claims an incoming offer. Serializes concurrent claims; returns `200 OK` on success, `409 Conflict` if already claimed by another donor.

### `POST /api/v1/donors/offers/{offer_id}/reject`
Declines an offer and returns donor to `AVAILABLE` state.
```json
{ "offer_id": "...", "rejection_reason": "Too far" }
```

---

## 3. Blood Request Endpoints

### `POST /api/v1/requests/`
Creates a blood request and immediately triggers Wave 1 dispatch.
```json
{
  "patient_name": "Anisur Rahman",
  "blood_group": "B+",
  "component": "WHOLE_BLOOD",
  "units_needed": 1,
  "hospital_name": "Square Hospital",
  "latitude": 23.7533,
  "longitude": 90.3817,
  "urgency": "CRITICAL_IMMEDIATE",
  "contact_phone": "+8801711111111"
}
```

### `GET /api/v1/requests/`
Lists blood requests with filtering by `status`, `blood_group`, or `urgency`.

### `GET /api/v1/requests/{request_id}`
Returns request details, active wave status, and confirmed donor contact information (phone revealed only upon acceptance).

### `POST /api/v1/requests/{request_id}/cancel`
Cancels request, revokes active offers, and notifies candidate donors.

### `POST /api/v1/requests/{request_id}/confirm`
Confirms physical completion of donation at the medical facility. Resets donor cooldown.

---

## 4. Simulator Endpoints

### `POST /api/v1/simulator/seed`
Seeds test accounts (Donors A, B, C, D, Requester, Admin, and Blood Banks).

### `GET /api/v1/simulator/state`
Returns the real-time state of all simulated entities.

### `POST /api/v1/simulator/trigger-request`
Triggers a sample B+ emergency request at Square Hospital.

### `POST /api/v1/simulator/simultaneous-accept`
Executes concurrent donor acceptances in parallel threads to test race condition handling.

### `POST /api/v1/simulator/wave-timeout`
Simulates wave timeout expiration and advances to the next wave.
