BEGIN TRANSACTION;
CREATE TABLE assignments (
  id TEXT PRIMARY KEY,
  request_id TEXT NOT NULL REFERENCES blood_requests(id),
  donor_id TEXT NOT NULL REFERENCES users(id),
  offer_id TEXT REFERENCES donor_offers(id),
  status TEXT DEFAULT 'ACTIVE',
  assigned_at TEXT,
  completed_at TEXT,
  notes TEXT
);
CREATE TABLE audit_logs (
  id TEXT PRIMARY KEY,
  user_id TEXT,
  action TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  resource_id TEXT,
  details TEXT,
  ip_address TEXT,
  created_at TEXT
);
CREATE TABLE blood_centers (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  type TEXT DEFAULT 'HOSPITAL_BANK',
  division TEXT DEFAULT 'Dhaka',
  district TEXT DEFAULT 'Dhaka',
  address TEXT NOT NULL,
  latitude REAL NOT NULL,
  longitude REAL NOT NULL,
  phone TEXT NOT NULL,
  helpline TEXT,
  is_verified INTEGER DEFAULT 1,
  available_stock_summary TEXT
);
CREATE TABLE blood_requests (
  id TEXT PRIMARY KEY,
  requester_id TEXT NOT NULL REFERENCES users(id),
  patient_name TEXT NOT NULL,
  blood_group TEXT NOT NULL,
  component TEXT DEFAULT 'WHOLE_BLOOD',
  units_needed INTEGER DEFAULT 1,
  units_fulfilled INTEGER DEFAULT 0,
  urgency TEXT DEFAULT 'URGENT',
  hospital_name TEXT NOT NULL,
  hospital_address TEXT,
  latitude REAL NOT NULL,
  longitude REAL NOT NULL,
  needed_by TEXT,
  notes TEXT,
  contact_phone TEXT NOT NULL,
  status TEXT DEFAULT 'MATCHING',
  current_wave INTEGER DEFAULT 1,
  created_at TEXT,
  updated_at TEXT
);
CREATE TABLE compatibility_policies (
  id TEXT PRIMARY KEY,
  version TEXT UNIQUE NOT NULL,
  policy_type TEXT DEFAULT 'ABO_RH_RED_CELLS',
  rules_json TEXT NOT NULL,
  is_active INTEGER DEFAULT 1,
  created_at TEXT
);
CREATE TABLE dispatch_waves (
  id TEXT PRIMARY KEY,
  request_id TEXT NOT NULL REFERENCES blood_requests(id) ON DELETE CASCADE,
  wave_number INTEGER NOT NULL,
  radius_km REAL NOT NULL,
  candidate_count INTEGER DEFAULT 0,
  timeout_seconds INTEGER DEFAULT 25,
  status TEXT DEFAULT 'ACTIVE',
  started_at TEXT,
  expires_at TEXT NOT NULL
);
CREATE TABLE donation_records (
  id TEXT PRIMARY KEY,
  assignment_id TEXT NOT NULL REFERENCES assignments(id),
  request_id TEXT NOT NULL REFERENCES blood_requests(id),
  donor_id TEXT NOT NULL REFERENCES users(id),
  hospital_name TEXT NOT NULL,
  units_donated INTEGER DEFAULT 1,
  donation_date TEXT,
  verified_by_admin_id TEXT
);
CREATE TABLE donor_offers (
  id TEXT PRIMARY KEY,
  wave_id TEXT NOT NULL REFERENCES dispatch_waves(id) ON DELETE CASCADE,
  request_id TEXT NOT NULL REFERENCES blood_requests(id) ON DELETE CASCADE,
  donor_id TEXT NOT NULL REFERENCES users(id),
  status TEXT DEFAULT 'OFFERED',
  sent_at TEXT,
  expires_at TEXT NOT NULL,
  responded_at TEXT,
  rejection_reason TEXT
);
CREATE TABLE donor_profiles (
  id TEXT PRIMARY KEY,
  user_id TEXT UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  blood_group TEXT NOT NULL,
  whatsapp_number TEXT,
  donation_intent TEXT DEFAULT 'REGULAR',
  area_district TEXT,
  date_of_birth TEXT,
  gender TEXT DEFAULT 'MALE',
  weight_kg REAL DEFAULT 60.0,
  availability_status TEXT DEFAULT 'AVAILABLE',
  latitude REAL NOT NULL DEFAULT 23.8103,
  longitude REAL NOT NULL DEFAULT 90.4125,
  address TEXT,
  preferred_radius_km REAL DEFAULT 15.0,
  last_donation_date TEXT,
  total_donations INTEGER DEFAULT 0,
  reliability_score REAL DEFAULT 1.0,
  response_count INTEGER DEFAULT 0,
  accepted_count INTEGER DEFAULT 0,
  rejected_count INTEGER DEFAULT 0,
  timeout_count INTEGER DEFAULT 0,
  active_assignment_id TEXT,
  fcm_token TEXT,
  created_at TEXT,
  updated_at TEXT
);
CREATE TABLE requester_profiles (
  id TEXT PRIMARY KEY,
  user_id TEXT UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  alternate_phone TEXT,
  created_at TEXT
);
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  phone TEXT UNIQUE NOT NULL,
  email TEXT UNIQUE,
  full_name TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'DONOR',
  is_verified INTEGER NOT NULL DEFAULT 1,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT,
  updated_at TEXT
);
INSERT INTO "users" VALUES('9610b54a-b568-4bf2-9fb9-73149fcef637','+8801700000000','admin@bloodhub.org.bd','Blood Hub Administrator','a8d368ce56da095ceefbebcaaa44aed9$c2b6aed187f6242c0470d33f4ce1475ca3b4865be6a9320dfbf10577b3a71076','ADMIN',1,1,'2026-09-21T08:47:36.679130','2026-09-21T08:47:36.679130');
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_donor_status_coords ON donor_profiles(availability_status, latitude, longitude);
CREATE INDEX idx_donor_blood ON donor_profiles(blood_group);
CREATE INDEX idx_req_status ON blood_requests(status);
CREATE INDEX idx_waves_req ON dispatch_waves(request_id);
CREATE INDEX idx_offers_status ON donor_offers(status);
COMMIT;
