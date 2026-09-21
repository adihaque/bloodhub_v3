# Blood Hub: Database Architecture & Schema Specification

Blood Hub uses an ACID-compliant relational schema supporting both SQLite and PostgreSQL.

---

## 1. Relational Entities (Tables)

```
users (1) ───< (1) donor_profiles
users (1) ───< (1) requester_profiles
users (1) ───< (*) blood_requests
blood_requests (1) ───< (*) dispatch_waves
dispatch_waves (1) ───< (*) donor_offers
blood_requests (1) ───< (*) assignments
assignments (1) ───< (1) donation_records
blood_centers (Verified Institutional Directory)
audit_logs (Immutable System Audit Trail)
compatibility_policies (Versioned ABO/Rh Policy Matrix)
```

---

## 2. Schema Definitions

### `users`
- `id` (TEXT PRIMARY KEY)
- `phone` (TEXT UNIQUE NOT NULL, INDEXED)
- `email` (TEXT UNIQUE)
- `full_name` (TEXT NOT NULL)
- `password_hash` (TEXT NOT NULL)
- `role` (TEXT NOT NULL DEFAULT 'DONOR')
- `is_verified` (INTEGER DEFAULT 1)
- `is_active` (INTEGER DEFAULT 1)
- `created_at`, `updated_at` (TEXT)

### `donor_profiles`
- `id` (TEXT PRIMARY KEY)
- `user_id` (TEXT UNIQUE NOT NULL REFERENCES users(id))
- `blood_group` (TEXT NOT NULL, INDEXED)
- `availability_status` (TEXT DEFAULT 'AVAILABLE', INDEXED)
- `latitude`, `longitude` (REAL NOT NULL, COMPOSITE INDEXED)
- `preferred_radius_km` (REAL DEFAULT 15.0)
- `last_donation_date` (TEXT)
- `total_donations` (INTEGER DEFAULT 0)
- `reliability_score` (REAL DEFAULT 1.0)
- `response_count`, `accepted_count`, `rejected_count`, `timeout_count` (INTEGER)
- `active_assignment_id` (TEXT)

### `blood_requests`
- `id` (TEXT PRIMARY KEY)
- `requester_id` (TEXT NOT NULL REFERENCES users(id))
- `patient_name` (TEXT NOT NULL)
- `blood_group` (TEXT NOT NULL, INDEXED)
- `component` (TEXT DEFAULT 'WHOLE_BLOOD')
- `units_needed` (INTEGER DEFAULT 1)
- `units_fulfilled` (INTEGER DEFAULT 0)
- `urgency` (TEXT DEFAULT 'URGENT')
- `hospital_name` (TEXT NOT NULL)
- `latitude`, `longitude` (REAL NOT NULL)
- `contact_phone` (TEXT NOT NULL)
- `status` (TEXT DEFAULT 'MATCHING', INDEXED)
- `current_wave` (INTEGER DEFAULT 1)

### `dispatch_waves`
- `id` (TEXT PRIMARY KEY)
- `request_id` (TEXT NOT NULL REFERENCES blood_requests(id))
- `wave_number` (INTEGER NOT NULL)
- `radius_km` (REAL NOT NULL)
- `candidate_count` (INTEGER DEFAULT 0)
- `timeout_seconds` (INTEGER DEFAULT 25)
- `status` (TEXT DEFAULT 'ACTIVE')
- `started_at`, `expires_at` (TEXT)

### `donor_offers`
- `id` (TEXT PRIMARY KEY)
- `wave_id` (TEXT NOT NULL REFERENCES dispatch_waves(id))
- `request_id` (TEXT NOT NULL REFERENCES blood_requests(id))
- `donor_id` (TEXT NOT NULL REFERENCES users(id))
- `status` (TEXT DEFAULT 'OFFERED', INDEXED)
- `sent_at`, `expires_at`, `responded_at` (TEXT)
- `rejection_reason` (TEXT)

### `assignments`
- `id` (TEXT PRIMARY KEY)
- `request_id` (TEXT NOT NULL REFERENCES blood_requests(id))
- `donor_id` (TEXT NOT NULL REFERENCES users(id))
- `offer_id` (TEXT REFERENCES donor_offers(id))
- `status` (TEXT DEFAULT 'ACTIVE')
- `assigned_at`, `completed_at` (TEXT)
- `notes` (TEXT)
