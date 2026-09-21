"""
Donor platform eligibility screening.
Note: Platform eligibility filters unsuitable candidates at the application layer,
but is NOT clinical or medical clearance. The receiving hospital/blood bank remains
solely responsible for laboratory screening, cross-matching, and clinical clearance.
"""
from datetime import datetime, date
from typing import Optional, Tuple
from bloodhub.core.config import settings

def calculate_age(birth_date_str: Optional[str]) -> Optional[int]:
    if not birth_date_str:
        return None
    try:
        parts = [int(p) for p in birth_date_str.split("-")]
        if len(parts) == 3:
            b_date = date(parts[0], parts[1], parts[2])
            today = date.today()
            return today.year - b_date.year - ((today.month, today.day) < (b_date.month, b_date.day))
    except Exception:
        return None
    return None

def check_donor_eligibility(
    availability_status: str,
    weight_kg: float,
    birth_date_str: Optional[str] = None,
    last_donation_date_str: Optional[str] = None,
    gender: str = "MALE",
    component: str = "WHOLE_BLOOD",
    active_assignment_id: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Evaluates whether a donor meets platform-level criteria for receiving an offer.
    Returns (is_eligible, reason).
    """
    # 1. Availability check
    if availability_status != "AVAILABLE":
        return False, f"Donor status is {availability_status}"
        
    # 2. Existing active assignment
    if active_assignment_id:
        return False, "Donor is currently assigned to another active emergency"
        
    # 3. Minimum weight
    if weight_kg < settings.MIN_WEIGHT_KG:
        return False, f"Weight ({weight_kg}kg) is below minimum platform threshold ({settings.MIN_WEIGHT_KG}kg)"
        
    # 4. Age constraints
    age = calculate_age(birth_date_str)
    if age is not None:
        if age < settings.MIN_DONOR_AGE:
            return False, f"Age ({age}) is below minimum threshold ({settings.MIN_DONOR_AGE})"
        if age > settings.MAX_DONOR_AGE:
            return False, f"Age ({age}) exceeds maximum platform threshold ({settings.MAX_DONOR_AGE})"
            
    # 5. Cooldown interval check
    if last_donation_date_str:
        try:
            parts = [int(p) for p in last_donation_date_str.split("-")]
            if len(parts) == 3:
                last_donated = date(parts[0], parts[1], parts[2])
                days_since = (date.today() - last_donated).days
                
                # Rule: Men 90 days, Women 120 days for whole blood
                cooldown_days = settings.DONATION_COOLDOWN_DAYS_WHOLE_BLOOD
                if gender.upper() == "FEMALE" and component.upper() == "WHOLE_BLOOD":
                    cooldown_days = 120
                elif component.upper() == "PLATELETS":
                    cooldown_days = settings.DONATION_COOLDOWN_DAYS_PLATELETS
                    
                if days_since < cooldown_days:
                    return False, f"Donation cooldown active ({days_since}/{cooldown_days} days elapsed)"
        except Exception:
            pass

    return True, "Eligible"
