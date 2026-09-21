"""
Centralized, versioned blood compatibility policy service.
Isolates clinical and logistical compatibility rules from the rest of the application.
"""
from typing import List, Dict

CURRENT_POLICY_VERSION = "v1.0-bd-standard"

# Red blood cells / Whole blood compatibility matrix
# Key: Recipient Blood Group -> Value: List of Compatible Donor Blood Groups
RED_CELL_COMPATIBILITY_V1: Dict[str, List[str]] = {
    "O-": ["O-"],
    "O+": ["O-", "O+"],
    "A-": ["O-", "A-"],
    "A+": ["O-", "O+", "A-", "A+"],
    "B-": ["O-", "B-"],
    "B+": ["O-", "O+", "B-", "B+"],
    "AB-": ["O-", "A-", "B-", "AB-"],
    "AB+": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]
}

# Plasma / Platelet compatibility matrix (inverse of red cells)
PLASMA_COMPATIBILITY_V1: Dict[str, List[str]] = {
    "O-": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
    "O+": ["O+", "A+", "B+", "AB+"],
    "A-": ["A-", "A+", "AB-", "AB+"],
    "A+": ["A+", "AB+"],
    "B-": ["B-", "B+", "AB-", "AB+"],
    "B+": ["B+", "AB+"],
    "AB-": ["AB-", "AB+"],
    "AB+": ["AB+"]
}

def normalize_blood_group(group: str) -> str:
    """Standardizes string representation e.g. 'O_POSITIVE' or 'O+' to 'O+'."""
    g = group.strip().upper().replace(" ", "")
    mapping = {
        "O_POSITIVE": "O+", "OPOSITIVE": "O+", "O+": "O+",
        "O_NEGATIVE": "O-", "ONEGATIVE": "O-", "O-": "O-",
        "A_POSITIVE": "A+", "APOSITIVE": "A+", "A+": "A+",
        "A_NEGATIVE": "A-", "ANEGATIVE": "A-", "A-": "A-",
        "B_POSITIVE": "B+", "BPOSITIVE": "B+", "B+": "B+",
        "B_NEGATIVE": "B-", "BNEGATIVE": "B-", "B-": "B-",
        "AB_POSITIVE": "AB+", "ABPOSITIVE": "AB+", "AB+": "AB+",
        "AB_NEGATIVE": "AB-", "ABNEGATIVE": "AB-", "AB-": "AB-"
    }
    return mapping.get(g, g)

def get_compatible_donor_groups(recipient_group: str, component: str = "WHOLE_BLOOD", policy_version: str = CURRENT_POLICY_VERSION) -> List[str]:
    """Returns list of compatible donor groups for a given recipient."""
    norm_recip = normalize_blood_group(recipient_group)
    comp = (component or "WHOLE_BLOOD").upper()
    if comp in ("PLASMA", "PLATELETS"):
        return PLASMA_COMPATIBILITY_V1.get(norm_recip, [norm_recip])
    # Default: Whole Blood / Red Blood Cells
    return RED_CELL_COMPATIBILITY_V1.get(norm_recip, [norm_recip])

def is_compatible(donor_group: str, recipient_group: str, component: str = "WHOLE_BLOOD") -> bool:
    """Checks if a donor's blood group is compatible with recipient."""
    norm_donor = normalize_blood_group(donor_group)
    norm_recip = normalize_blood_group(recipient_group)
    compatibles = get_compatible_donor_groups(norm_recip, component)
    return norm_donor in compatibles
