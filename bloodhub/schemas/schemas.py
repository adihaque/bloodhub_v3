from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# User & Auth Schemas
class UserRegister(BaseModel):
    phone: str
    password: str
    full_name: str
    role: str = "DONOR"  # DONOR, REQUESTER, ADMIN
    email: Optional[str] = None
    
    # Donor Profile fields
    blood_group: Optional[str] = "B+"
    whatsapp_number: Optional[str] = None
    donation_intent: Optional[str] = "REGULAR"  # REGULAR, WHEN_NEEDED, DONATE_LATER
    last_donation_date: Optional[str] = None
    area_district: Optional[str] = "Dhaka"
    
    # Location
    latitude: Optional[float] = 23.8103
    longitude: Optional[float] = 90.4125
    address: Optional[str] = "Dhaka, Bangladesh"
    preferred_radius_km: Optional[float] = 15.0

    # Basic Eligibility
    date_of_birth: Optional[str] = "1998-01-01"
    gender: Optional[str] = "MALE"
    weight_kg: Optional[float] = 60.0

class UserLogin(BaseModel):
    phone: str
    password: str

class UserOut(BaseModel):
    id: str
    phone: str
    email: Optional[str]
    full_name: str
    role: str
    is_verified: bool
    is_active: bool
    created_at: Optional[str]
    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    user: UserOut

# Donor Schemas
class LocationUpdate(BaseModel):
    latitude: float
    longitude: float
    address: Optional[str] = None
    area_district: Optional[str] = None

class AvailabilityUpdate(BaseModel):
    availability_status: str  # AVAILABLE, UNAVAILABLE

class DonorProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    whatsapp_number: Optional[str] = None
    blood_group: Optional[str] = None
    donation_intent: Optional[str] = None
    last_donation_date: Optional[str] = None
    area_district: Optional[str] = None
    availability_status: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    preferred_radius_km: Optional[float] = None
    weight_kg: Optional[float] = None

class DonorProfileOut(BaseModel):
    id: str
    user_id: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    blood_group: str
    whatsapp_number: Optional[str] = None
    donation_intent: Optional[str] = "REGULAR"
    area_district: Optional[str] = None
    date_of_birth: Optional[str]
    gender: Optional[str]
    weight_kg: Optional[float]
    availability_status: str
    latitude: float
    longitude: float
    address: Optional[str]
    preferred_radius_km: Optional[float]
    last_donation_date: Optional[str]
    total_donations: int
    reliability_score: float
    active_assignment_id: Optional[str]
    class Config:
        orm_mode = True

class DonorOfferOut(BaseModel):
    id: str
    wave_id: str
    request_id: str
    donor_id: str
    status: str
    sent_at: str
    expires_at: str
    seconds_remaining: Optional[int] = 25
    hospital_name: Optional[str]
    hospital_address: Optional[str]
    patient_name: Optional[str]
    blood_group: Optional[str]
    urgency: Optional[str]
    distance_km: Optional[float]
    class Config:
        orm_mode = True

class OfferResponse(BaseModel):
    offer_id: str
    rejection_reason: Optional[str] = None

# Request Schemas
class BloodRequestCreate(BaseModel):
    patient_name: str
    blood_group: str
    component: str = "WHOLE_BLOOD"
    units_needed: int = 1
    urgency: str = "URGENT"
    hospital_name: str
    hospital_address: Optional[str] = "Dhaka, Bangladesh"
    latitude: float
    longitude: float
    needed_by: Optional[datetime] = None
    notes: Optional[str] = None
    contact_phone: str

class BloodRequestOut(BaseModel):
    id: str
    requester_id: str
    patient_name: str
    blood_group: str
    component: str
    units_needed: int
    units_fulfilled: int
    urgency: str
    hospital_name: str
    hospital_address: Optional[str]
    latitude: float
    longitude: float
    needed_by: Optional[str]
    notes: Optional[str]
    contact_phone: str
    status: str
    current_wave: int
    created_at: str
    class Config:
        orm_mode = True

class RequestCancel(BaseModel):
    reason: Optional[str] = "Sourced elsewhere"

class DonationConfirm(BaseModel):
    notes: Optional[str] = None

class BloodCenterOut(BaseModel):
    id: str
    name: str
    type: str
    division: str
    district: str
    address: str
    latitude: float
    longitude: float
    phone: str
    helpline: Optional[str]
    is_verified: bool
    available_stock_summary: Optional[str]
    distance_km: Optional[float] = None
    class Config:
        orm_mode = True

class BloodCenterCreate(BaseModel):
    name: str
    type: str = "HOSPITAL_BANK"
    division: str = "Dhaka"
    district: str = "Dhaka"
    address: str
    latitude: float
    longitude: float
    phone: str
    helpline: Optional[str] = None
    available_stock_summary: Optional[str] = None

class SystemMetricsOut(BaseModel):
    total_donors: int
    available_donors: int
    total_requests: int
    active_requests: int
    fulfilled_requests: int
    total_assignments: int
    acceptance_rate: float
    active_waves: int
    active_environment: str = "pilot"

class AuditLogOut(BaseModel):
    id: str
    user_id: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Optional[str]
    ip_address: Optional[str]
    created_at: str
    class Config:
        orm_mode = True

# Algorithm & Inspection Schemas
class AlgorithmConfigUpdate(BaseModel):
    compatibility_exact_pts: Optional[float] = None
    compatibility_compatible_pts: Optional[float] = None
    proximity_weight_pts: Optional[float] = None
    reliability_weight_pts: Optional[float] = None
    interval_weight_pts: Optional[float] = None
    intent_regular_bonus: Optional[float] = None
    intent_when_needed_bonus: Optional[float] = None
    cooldown_days: Optional[int] = None
    wave1_radius_km: Optional[float] = None
    wave1_timeout_sec: Optional[int] = None
    wave1_candidates: Optional[int] = None
    wave2_radius_km: Optional[float] = None
    wave2_timeout_sec: Optional[int] = None
    wave2_candidates: Optional[int] = None
    wave3_radius_km: Optional[float] = None
    wave3_timeout_sec: Optional[int] = None
    wave3_candidates: Optional[int] = None
    wave4_radius_km: Optional[float] = None
    wave4_timeout_sec: Optional[int] = None
    wave4_candidates: Optional[int] = None
    auto_dispatch_whatsapp: Optional[int] = None
    auto_dispatch_in_app: Optional[int] = None
    auto_dispatch_sms: Optional[int] = None

class AlgorithmConfigOut(BaseModel):
    id: str
    compatibility_exact_pts: float
    compatibility_compatible_pts: float
    proximity_weight_pts: float
    reliability_weight_pts: float
    interval_weight_pts: float
    intent_regular_bonus: float
    intent_when_needed_bonus: float
    cooldown_days: int
    wave1_radius_km: float
    wave1_timeout_sec: int
    wave1_candidates: int
    wave2_radius_km: float
    wave2_timeout_sec: int
    wave2_candidates: int
    wave3_radius_km: float
    wave3_timeout_sec: int
    wave3_candidates: int
    wave4_radius_km: float
    wave4_timeout_sec: int
    wave4_candidates: int
    auto_dispatch_whatsapp: int
    auto_dispatch_in_app: int
    auto_dispatch_sms: int
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
    class Config:
        orm_mode = True

class AlgorithmPreviewRequest(BaseModel):
    blood_group: str = "B+"
    component: str = "WHOLE_BLOOD"
    hospital_name: Optional[str] = "Square Hospital"
    hospital_address: Optional[str] = "Panthapath, Dhaka"
    latitude: float = 23.7533
    longitude: float = 90.3817
    radius_km: float = 10.0
    max_candidates: int = 10
