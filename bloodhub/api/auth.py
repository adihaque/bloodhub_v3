from fastapi import APIRouter, Depends, HTTPException, status
from bloodhub.core.database import get_db, DatabaseSession
from bloodhub.core.security import hash_password, verify_password, create_access_token
from bloodhub.models.models import User, DonorProfile, RequesterProfile, AuditLog
from bloodhub.schemas.schemas import UserRegister, UserLogin, Token, UserOut
from bloodhub.api.deps import get_current_user
from bloodhub.domain.compatibility import normalize_blood_group

router = APIRouter(prefix="/auth", tags=["Authentication"])

def normalize_bd_phone(phone: str) -> str:
    """Standardizes Bangladeshi mobile numbers into +8801XXXXXXXXX format."""
    p = phone.strip().replace(" ", "").replace("-", "")
    if p.startswith("+880"):
        return p
    if p.startswith("880"):
        return f"+{p}"
    if p.startswith("01") and len(p) == 11:
        return f"+88{p}"
    return p

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserRegister, db: DatabaseSession = Depends(get_db)):
    clean_phone = normalize_bd_phone(payload.phone)
    if len(clean_phone) < 11:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid 11-digit mobile number."
        )

    existing_user = db.query(User).filter_by(phone=clean_phone).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An account with phone number {clean_phone} already exists. Please log in."
        )

    if payload.email:
        clean_email = payload.email.strip().lower()
        if db.query(User).filter_by(email=clean_email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"An account with email {clean_email} already exists."
            )
    else:
        clean_email = None

    new_user = User(
        phone=clean_phone,
        email=clean_email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=payload.role.upper(),
        is_verified=1,
        is_active=1
    )
    db.add(new_user)
    db.flush()

    if new_user.role == "DONOR":
        norm_blood = normalize_blood_group(payload.blood_group or "B+")
        intent = (payload.donation_intent or "REGULAR").upper()
        initial_avail = "AVAILABLE" if intent != "DONATE_LATER" else "UNAVAILABLE"
        
        wa_number = normalize_bd_phone(payload.whatsapp_number) if payload.whatsapp_number else clean_phone
        area = payload.area_district.strip() if payload.area_district else "Dhaka"
        address = payload.address.strip() if payload.address else f"{area}, Bangladesh"

        donor_profile = DonorProfile(
            user_id=new_user.id,
            blood_group=norm_blood,
            whatsapp_number=wa_number,
            donation_intent=intent,
            area_district=area,
            date_of_birth=payload.date_of_birth or "1998-01-01",
            gender=payload.gender or "MALE",
            weight_kg=payload.weight_kg or 60.0,
            availability_status=initial_avail,
            latitude=payload.latitude if payload.latitude is not None else 23.8103,
            longitude=payload.longitude if payload.longitude is not None else 90.4125,
            address=address,
            preferred_radius_km=payload.preferred_radius_km or 15.0,
            last_donation_date=payload.last_donation_date or None
        )
        db.add(donor_profile)
    elif new_user.role == "REQUESTER":
        requester_profile = RequesterProfile(
            user_id=new_user.id
        )
        db.add(requester_profile)

    audit = AuditLog(
        user_id=new_user.id,
        action="DONOR_REGISTERED" if new_user.role == "DONOR" else "USER_REGISTERED",
        resource_type="User",
        resource_id=new_user.id,
        details=f"User {new_user.full_name} ({new_user.phone}) registered."
    )
    db.add(audit)
    db.commit()
    db.refresh(new_user)

    token = create_access_token({"sub": new_user.id, "role": new_user.role})
    return {
        "access_token": token,
        "token_type": "Bearer",
        "user": new_user.to_dict()
    }

@router.post("/login", response_model=Token)
def login_user(payload: UserLogin, db: DatabaseSession = Depends(get_db)):
    clean_phone = normalize_bd_phone(payload.phone)
    user = db.query(User).filter_by(phone=clean_phone).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number or password."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Please contact support."
        )

    token = create_access_token({"sub": user.id, "role": user.role})
    return {
        "access_token": token,
        "token_type": "Bearer",
        "user": user.to_dict()
    }

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user.to_dict()
