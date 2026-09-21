import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from bloodhub.core.database import create_connection
from bloodhub.core.config import settings

def generate_uuid() -> str:
    return str(uuid.uuid4())

class BaseModel:
    __tablename__: str = ""
    __fields__: Dict[str, str] = {}

    def __init__(self, **kwargs):
        self._session = None
        for field in self.__fields__:
            default_val = None
            if field == "id":
                default_val = kwargs.get("id") or generate_uuid()
            elif field in ("created_at", "updated_at", "started_at", "sent_at", "assigned_at", "donation_date"):
                default_val = kwargs.get(field) or datetime.utcnow().isoformat()
            setattr(self, field, kwargs.get(field, default_val))

    @classmethod
    def from_row(cls, row, session=None):
        if not row:
            return None
        kwargs = {}
        for k in row.keys():
            kwargs[k] = row[k]
        obj = cls(**kwargs)
        obj._session = session
        return obj

    def to_dict(self) -> Dict[str, Any]:
        return {f: getattr(self, f, None) for f in self.__fields__}

    def _save(self, session):
        conn = session.conn
        data = self.to_dict()
        
        cur = conn.cursor()
        cur.execute(f"SELECT 1 FROM {self.__tablename__} WHERE id = ?", [self.id])
        exists = cur.fetchone() is not None

        if exists:
            update_fields = [f for f in self.__fields__ if f != "id"]
            if "updated_at" in self.__fields__:
                data["updated_at"] = datetime.utcnow().isoformat()
                setattr(self, "updated_at", data["updated_at"])
            set_clauses = [f"{f} = ?" for f in update_fields]
            values = [data[f] for f in update_fields] + [self.id]
            sql = f"UPDATE {self.__tablename__} SET {', '.join(set_clauses)} WHERE id = ?"
            cur.execute(sql, values)
        else:
            fields = list(self.__fields__.keys())
            placeholders = ["?"] * len(fields)
            values = [data[f] for f in fields]
            sql = f"INSERT INTO {self.__tablename__} ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
            cur.execute(sql, values)

class User(BaseModel):
    __tablename__ = "users"
    __fields__ = {
        "id": "TEXT PRIMARY KEY",
        "phone": "TEXT UNIQUE NOT NULL",
        "email": "TEXT UNIQUE",
        "full_name": "TEXT NOT NULL",
        "password_hash": "TEXT NOT NULL",
        "role": "TEXT NOT NULL DEFAULT 'DONOR'",
        "is_verified": "INTEGER NOT NULL DEFAULT 1",
        "is_active": "INTEGER NOT NULL DEFAULT 1",
        "created_at": "TEXT",
        "updated_at": "TEXT"
    }

class DonorProfile(BaseModel):
    __tablename__ = "donor_profiles"
    __fields__ = {
        "id": "TEXT PRIMARY KEY",
        "user_id": "TEXT UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE",
        "blood_group": "TEXT NOT NULL",
        "whatsapp_number": "TEXT",
        "donation_intent": "TEXT DEFAULT 'REGULAR'",  # REGULAR, WHEN_NEEDED, DONATE_LATER
        "area_district": "TEXT",
        "date_of_birth": "TEXT",
        "gender": "TEXT DEFAULT 'MALE'",
        "weight_kg": "REAL DEFAULT 60.0",
        "availability_status": "TEXT DEFAULT 'AVAILABLE'",
        "latitude": "REAL NOT NULL DEFAULT 23.8103",
        "longitude": "REAL NOT NULL DEFAULT 90.4125",
        "address": "TEXT",
        "preferred_radius_km": "REAL DEFAULT 15.0",
        "last_donation_date": "TEXT",
        "total_donations": "INTEGER DEFAULT 0",
        "reliability_score": "REAL DEFAULT 1.0",
        "response_count": "INTEGER DEFAULT 0",
        "accepted_count": "INTEGER DEFAULT 0",
        "rejected_count": "INTEGER DEFAULT 0",
        "timeout_count": "INTEGER DEFAULT 0",
        "active_assignment_id": "TEXT",
        "fcm_token": "TEXT",
        "created_at": "TEXT",
        "updated_at": "TEXT"
    }

class RequesterProfile(BaseModel):
    __tablename__ = "requester_profiles"
    __fields__ = {
        "id": "TEXT PRIMARY KEY",
        "user_id": "TEXT UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE",
        "alternate_phone": "TEXT",
        "created_at": "TEXT"
    }

class BloodRequest(BaseModel):
    __tablename__ = "blood_requests"
    __fields__ = {
        "id": "TEXT PRIMARY KEY",
        "requester_id": "TEXT NOT NULL REFERENCES users(id)",
        "patient_name": "TEXT NOT NULL",
        "blood_group": "TEXT NOT NULL",
        "component": "TEXT DEFAULT 'WHOLE_BLOOD'",
        "units_needed": "INTEGER DEFAULT 1",
        "units_fulfilled": "INTEGER DEFAULT 0",
        "urgency": "TEXT DEFAULT 'URGENT'",
        "hospital_name": "TEXT NOT NULL",
        "hospital_address": "TEXT",
        "latitude": "REAL NOT NULL",
        "longitude": "REAL NOT NULL",
        "needed_by": "TEXT",
        "notes": "TEXT",
        "contact_phone": "TEXT NOT NULL",
        "status": "TEXT DEFAULT 'MATCHING'",
        "current_wave": "INTEGER DEFAULT 1",
        "created_at": "TEXT",
        "updated_at": "TEXT"
    }

class DispatchWave(BaseModel):
    __tablename__ = "dispatch_waves"
    __fields__ = {
        "id": "TEXT PRIMARY KEY",
        "request_id": "TEXT NOT NULL REFERENCES blood_requests(id) ON DELETE CASCADE",
        "wave_number": "INTEGER NOT NULL",
        "radius_km": "REAL NOT NULL",
        "candidate_count": "INTEGER DEFAULT 0",
        "timeout_seconds": "INTEGER DEFAULT 25",
        "status": "TEXT DEFAULT 'ACTIVE'",
        "started_at": "TEXT",
        "expires_at": "TEXT NOT NULL"
    }

class DonorOffer(BaseModel):
    __tablename__ = "donor_offers"
    __fields__ = {
        "id": "TEXT PRIMARY KEY",
        "wave_id": "TEXT NOT NULL REFERENCES dispatch_waves(id) ON DELETE CASCADE",
        "request_id": "TEXT NOT NULL REFERENCES blood_requests(id) ON DELETE CASCADE",
        "donor_id": "TEXT NOT NULL REFERENCES users(id)",
        "status": "TEXT DEFAULT 'OFFERED'",
        "channels": "TEXT DEFAULT 'IN_APP,WHATSAPP'",
        "score": "REAL DEFAULT 0.0",
        "distance_km": "REAL DEFAULT 0.0",
        "score_breakdown": "TEXT",
        "whatsapp_url": "TEXT",
        "whatsapp_status": "TEXT DEFAULT 'DELIVERED'",
        "in_app_status": "TEXT DEFAULT 'DELIVERED'",
        "sms_status": "TEXT DEFAULT 'SENT'",
        "sent_at": "TEXT",
        "expires_at": "TEXT NOT NULL",
        "responded_at": "TEXT",
        "response_latency_seconds": "REAL",
        "rejection_reason": "TEXT"
    }

class Assignment(BaseModel):
    __tablename__ = "assignments"
    __fields__ = {
        "id": "TEXT PRIMARY KEY",
        "request_id": "TEXT NOT NULL REFERENCES blood_requests(id)",
        "donor_id": "TEXT NOT NULL REFERENCES users(id)",
        "offer_id": "TEXT REFERENCES donor_offers(id)",
        "status": "TEXT DEFAULT 'ACTIVE'",
        "assigned_at": "TEXT",
        "completed_at": "TEXT",
        "notes": "TEXT"
    }

class DonationRecord(BaseModel):
    __tablename__ = "donation_records"
    __fields__ = {
        "id": "TEXT PRIMARY KEY",
        "assignment_id": "TEXT NOT NULL REFERENCES assignments(id)",
        "request_id": "TEXT NOT NULL REFERENCES blood_requests(id)",
        "donor_id": "TEXT NOT NULL REFERENCES users(id)",
        "hospital_name": "TEXT NOT NULL",
        "units_donated": "INTEGER DEFAULT 1",
        "donation_date": "TEXT",
        "verified_by_admin_id": "TEXT"
    }

class BloodCenter(BaseModel):
    __tablename__ = "blood_centers"
    __fields__ = {
        "id": "TEXT PRIMARY KEY",
        "name": "TEXT NOT NULL",
        "type": "TEXT DEFAULT 'HOSPITAL_BANK'",
        "division": "TEXT DEFAULT 'Dhaka'",
        "district": "TEXT DEFAULT 'Dhaka'",
        "address": "TEXT NOT NULL",
        "latitude": "REAL NOT NULL",
        "longitude": "REAL NOT NULL",
        "phone": "TEXT NOT NULL",
        "helpline": "TEXT",
        "is_verified": "INTEGER DEFAULT 1",
        "available_stock_summary": "TEXT"
    }

class AuditLog(BaseModel):
    __tablename__ = "audit_logs"
    __fields__ = {
        "id": "TEXT PRIMARY KEY",
        "user_id": "TEXT",
        "action": "TEXT NOT NULL",
        "resource_type": "TEXT NOT NULL",
        "resource_id": "TEXT",
        "details": "TEXT",
        "ip_address": "TEXT",
        "created_at": "TEXT"
    }

class CompatibilityPolicy(BaseModel):
    __tablename__ = "compatibility_policies"
    __fields__ = {
        "id": "TEXT PRIMARY KEY",
        "version": "TEXT UNIQUE NOT NULL",
        "policy_type": "TEXT DEFAULT 'ABO_RH_RED_CELLS'",
        "rules_json": "TEXT NOT NULL",
        "is_active": "INTEGER DEFAULT 1",
        "created_at": "TEXT"
    }

class AlgorithmConfig(BaseModel):
    __tablename__ = "algorithm_config"
    __fields__ = {
        "id": "TEXT PRIMARY KEY",
        "compatibility_exact_pts": "REAL DEFAULT 40.0",
        "compatibility_compatible_pts": "REAL DEFAULT 25.0",
        "proximity_weight_pts": "REAL DEFAULT 35.0",
        "reliability_weight_pts": "REAL DEFAULT 15.0",
        "interval_weight_pts": "REAL DEFAULT 10.0",
        "intent_regular_bonus": "REAL DEFAULT 5.0",
        "intent_when_needed_bonus": "REAL DEFAULT 2.0",
        "cooldown_days": "INTEGER DEFAULT 90",
        "wave1_radius_km": "REAL DEFAULT 5.0",
        "wave1_timeout_sec": "INTEGER DEFAULT 25",
        "wave1_candidates": "INTEGER DEFAULT 4",
        "wave2_radius_km": "REAL DEFAULT 8.0",
        "wave2_timeout_sec": "INTEGER DEFAULT 25",
        "wave2_candidates": "INTEGER DEFAULT 6",
        "wave3_radius_km": "REAL DEFAULT 15.0",
        "wave3_timeout_sec": "INTEGER DEFAULT 30",
        "wave3_candidates": "INTEGER DEFAULT 10",
        "wave4_radius_km": "REAL DEFAULT 25.0",
        "wave4_timeout_sec": "INTEGER DEFAULT 35",
        "wave4_candidates": "INTEGER DEFAULT 15",
        "auto_dispatch_whatsapp": "INTEGER DEFAULT 1",
        "auto_dispatch_in_app": "INTEGER DEFAULT 1",
        "auto_dispatch_sms": "INTEGER DEFAULT 1",
        "updated_at": "TEXT",
        "updated_by": "TEXT"
    }

ALL_MODELS = [
    AlgorithmConfig,
    User, DonorProfile, RequesterProfile, BloodRequest,
    DispatchWave, DonorOffer, Assignment, DonationRecord,
    BloodCenter, AuditLog, CompatibilityPolicy
]

def create_all(conn=None):
    close_after = False
    if conn is None:
        conn = create_connection()
        close_after = True

    cur = conn.cursor()
    for model in ALL_MODELS:
        # Check if table exists
        cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{model.__tablename__}';")
        tbl_exists = cur.fetchone() is not None

        if not tbl_exists:
            cols = [f"{name} {def_sql}" for name, def_sql in model.__fields__.items()]
            sql = f"CREATE TABLE IF NOT EXISTS {model.__tablename__} (\n  " + ",\n  ".join(cols) + "\n);"
            cur.execute(sql)
        else:
            # Perform additive column migrations if new fields were added
            cur.execute(f"PRAGMA table_info({model.__tablename__});")
            existing_cols = {row[1] for row in cur.fetchall()}
            for col_name, col_def in model.__fields__.items():
                if col_name not in existing_cols:
                    # Clean type definition (drop PRIMARY KEY if any)
                    clean_def = col_def.replace("PRIMARY KEY", "").strip()
                    cur.execute(f"ALTER TABLE {model.__tablename__} ADD COLUMN {col_name} {clean_def};")

    # Indices
    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_donor_status_coords ON donor_profiles(availability_status, latitude, longitude);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_donor_blood ON donor_profiles(blood_group);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_req_status ON blood_requests(status);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_waves_req ON dispatch_waves(request_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_offers_status ON donor_offers(status);")

    # Automatic Administrator Bootstrapping
    # Ensures the owner always has an active admin account to log into
    from bloodhub.core.security import hash_password
    cur.execute("SELECT id FROM users WHERE phone = ?", [settings.ADMIN_PHONE])
    admin_row = cur.fetchone()
    if not admin_row:
        admin_id = generate_uuid()
        now_ts = datetime.utcnow().isoformat()
        cur.execute(
            "INSERT INTO users (id, phone, email, full_name, password_hash, role, is_verified, is_active, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?, ?)",
            [
                admin_id,
                settings.ADMIN_PHONE,
                settings.ADMIN_EMAIL,
                settings.ADMIN_NAME,
                hash_password(settings.ADMIN_PASSWORD),
                "ADMIN",
                now_ts,
                now_ts
            ]
        )

    # Automatic Algorithm Config Bootstrapping
    cur.execute("SELECT id FROM algorithm_config WHERE id = 'active_config'")
    if not cur.fetchone():
        now_ts = datetime.utcnow().isoformat()
        cur.execute(
            "INSERT INTO algorithm_config (id, compatibility_exact_pts, compatibility_compatible_pts, "
            "proximity_weight_pts, reliability_weight_pts, interval_weight_pts, intent_regular_bonus, "
            "intent_when_needed_bonus, cooldown_days, wave1_radius_km, wave1_timeout_sec, wave1_candidates, "
            "wave2_radius_km, wave2_timeout_sec, wave2_candidates, wave3_radius_km, wave3_timeout_sec, "
            "wave3_candidates, wave4_radius_km, wave4_timeout_sec, wave4_candidates, auto_dispatch_whatsapp, "
            "auto_dispatch_in_app, auto_dispatch_sms, updated_at, updated_by) "
            "VALUES ('active_config', 40.0, 25.0, 35.0, 15.0, 10.0, 5.0, 2.0, 90, 5.0, 25, 4, 8.0, 25, 6, "
            "15.0, 30, 10, 25.0, 35, 15, 1, 1, 1, ?, 'system')",
            [now_ts]
        )

    conn.commit()
    if close_after:
        conn.close()

class _Base:
    metadata = type("Metadata", (), {"create_all": staticmethod(lambda bind=None: create_all())})()

Base = _Base()
