"""
Deterministic, explainable candidate ranking algorithm.
Avoids opaque black-box AI logic in favor of transparent medical and logistical factors.
"""
from datetime import date
from typing import Dict, Any
from bloodhub.domain.compatibility import normalize_blood_group

def calculate_candidate_score(
    donor_blood_group: str,
    recipient_blood_group: str,
    distance_km: float,
    max_radius_km: float,
    reliability_score: float = 1.0,
    last_donation_date_str: str = None
) -> Dict[str, Any]:
    """
    Computes deterministic ranking score (0 - 100) and breakdown factors.
    """
    norm_donor = normalize_blood_group(donor_blood_group)
    norm_recip = normalize_blood_group(recipient_blood_group)

    # 1. Compatibility Factor (Max 40 pts)
    # Exact match is preferred to conserve universal red cell stock (e.g. O-)
    if norm_donor == norm_recip:
        compat_score = 40.0
        compat_reason = "Exact blood group match"
    else:
        compat_score = 25.0
        compat_reason = "Compatible universal/alternative match"

    # 2. Distance / Proximity Factor (Max 35 pts)
    clamped_radius = max(max_radius_km, 1.0)
    dist_ratio = min(distance_km / clamped_radius, 1.0)
    distance_score = round(35.0 * (1.0 - dist_ratio), 2)

    # 3. Reliability & Response History Factor (Max 15 pts)
    clamped_reliability = max(0.0, min(reliability_score, 1.0))
    rel_score = round(15.0 * clamped_reliability, 2)

    # 4. Donation Interval Buffer Factor (Max 10 pts)
    interval_score = 5.0  # default neutral
    if last_donation_date_str:
        try:
            parts = [int(p) for p in last_donation_date_str.split("-")]
            if len(parts) == 3:
                days = (date.today() - date(parts[0], parts[1], parts[2])).days
                if days > 180:
                    interval_score = 10.0
                elif days > 120:
                    interval_score = 8.0
                elif days >= 90:
                    interval_score = 6.0
        except Exception:
            pass

    total_score = round(compat_score + distance_score + rel_score + interval_score, 2)

    return {
        "total_score": total_score,
        "breakdown": {
            "compatibility_points": compat_score,
            "compatibility_reason": compat_reason,
            "proximity_points": distance_score,
            "distance_km": distance_km,
            "reliability_points": rel_score,
            "interval_points": interval_score
        }
    }
