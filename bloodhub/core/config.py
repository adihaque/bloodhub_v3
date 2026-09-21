import os
from typing import List, Dict, Any
from pydantic import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Blood Hub"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment mode: 'pilot' (real users), 'development' (demo/dev), 'test'
    ENVIRONMENT: str = os.getenv("APP_ENV", "pilot").lower()
    DEBUG: bool = os.getenv("DEBUG", "false" if os.getenv("APP_ENV") == "pilot" else "true").lower() in ("true", "1", "yes")
    
    # Network Host
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "bloodhub-insecure-dev-secret-key-change-in-production-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days for mobile app convenience
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # Administrator Bootstrap Credentials (for the non-technical owner)
    ADMIN_PHONE: str = os.getenv("ADMIN_PHONE", "+8801700000000")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")
    ADMIN_NAME: str = os.getenv("ADMIN_NAME", "Blood Hub Administrator")
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@bloodhub.org.bd")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    DATABASE_BACKEND: str = os.getenv("DATABASE_BACKEND", "sqlite").lower()
    # Neon URLs are accepted as DATABASE_URL; these settings make deployment
    # explicit without forcing cloud dependencies in local mode.
    NEON_DATABASE_URL: str = os.getenv("NEON_DATABASE_URL", "")
    POSTGIS_ENABLED: bool = os.getenv("POSTGIS_ENABLED", "false").lower() in ("true", "1", "yes")

    # Optional distributed cache/session infrastructure (Upstash Redis).
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    UPSTASH_REDIS_REST_URL: str = os.getenv("UPSTASH_REDIS_REST_URL", "")
    UPSTASH_REDIS_REST_TOKEN: str = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
    REDIS_ENABLED: bool = os.getenv("REDIS_ENABLED", "false").lower() in ("true", "1", "yes")

    # Notification integrations default to safe no-op/mock providers.
    FCM_PROVIDER: str = os.getenv("FCM_PROVIDER", "mock").lower()
    FCM_PROJECT_ID: str = os.getenv("FCM_PROJECT_ID", "")
    FCM_CREDENTIALS_JSON: str = os.getenv("FCM_CREDENTIALS_JSON", "")
    SMS_PROVIDER: str = os.getenv("SMS_PROVIDER", "mock").lower()
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM_NUMBER: str = os.getenv("TWILIO_FROM_NUMBER", "")
    WHATSAPP_FROM_NUMBER: str = os.getenv("WHATSAPP_FROM_NUMBER", "")

    # Device sessions
    SESSION_TOKEN_EXPIRE_DAYS: int = int(os.getenv("SESSION_TOKEN_EXPIRE_DAYS", "30"))
    SESSION_TOKEN_BYTES: int = int(os.getenv("SESSION_TOKEN_BYTES", "32"))
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # Dispatch & Wave Settings
    DEFAULT_WAVES: List[Dict[str, Any]] = [
        {"wave_number": 1, "radius_km": 5.0, "candidate_count": 4, "timeout_seconds": 25},
        {"wave_number": 2, "radius_km": 8.0, "candidate_count": 6, "timeout_seconds": 25},
        {"wave_number": 3, "radius_km": 15.0, "candidate_count": 10, "timeout_seconds": 30},
        {"wave_number": 4, "radius_km": 25.0, "candidate_count": 15, "timeout_seconds": 35},
    ]
    
    # Medical Policy Defaults
    MIN_DONOR_AGE: int = 18
    MAX_DONOR_AGE: int = 60
    MIN_WEIGHT_KG: float = 50.0
    DONATION_COOLDOWN_DAYS_WHOLE_BLOOD: int = 90
    DONATION_COOLDOWN_DAYS_PLATELETS: int = 14
    
    # Location Fuzzing (Privacy)
    LOCATION_FUZZ_RADIUS_METERS: float = 800.0
    
    # Bangladesh Defaults
    DEFAULT_COUNTRY_CODE: str = "+880"
    DEFAULT_CITY: str = "Dhaka"
    DEFAULT_LATITUDE: float = 23.8103
    DEFAULT_LONGITUDE: float = 90.4125
    
    # Emergency Hotline Fallbacks (Institutional)
    NATIONAL_HEALTH_HELPLINE: str = "16263"
    NATIONAL_EMERGENCY_SERVICE: str = "999"
    RED_CRESCENT_HELPLINE: str = "+880248121182"
    QUANTUM_HELPLINE: str = "+8801714010869"
    BADHAN_HELPLINE: str = "+8801534982674"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
