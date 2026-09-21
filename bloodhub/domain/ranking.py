"""
Deterministic, explainable candidate ranking algorithm with dynamic administrative weighting.
Avoids opaque black-box AI logic in favor of transparent medical and logistical factors.
"""
from datetime import date
from typing import Dict, Any, Optional
from bloodhub.domain.compatibility import normalize_blood_group

def calculate_candidate_score(
    donor_blood_group: str,
    recipient_blood_group: str,
    distance_km: float,
    max_radius_km: float,
    reliability_score: float = 1.0,
    last_donation_date_str: Optional[str] = None,
    donation_intent: str = "REGULAR",
    config: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Computes deterministic ranking score (0 - 100+) and factor breakdown.
    Dynamically respects active AlgorithmConfig if provided.
    """
    norm_donor = normalize_blood_group(donor_blood_group)
    norm_recip = normalize_blood_group(recipient_blood_group)

    # Configurable weights (defaulting to standard clinical baseline)
    exact_pts = float(getattr(config, "compatibility_exact_pts", 40.0))
    compat_pts = float(getattr(config, "compatibility_compatible_pts", 25.0))
    prox_weight = float(getattr(config, "proximity_weight_pts", 35.0))
    rel_weight = float(getattr(config, "reliability_weight_pts", 15.0))
    interval_weight = float(getattr(config, "interval_weight_pts", 10.0))
    intent_reg_bonus = float(getattr(config, "intent_regular_bonus", 5.0))
    intent_needed_bonus = float(getattr(config, "intent_when_needed_bonus", 2.0))

    # 1. Compatibility Factor
    # Exact match is prioritized to conserve rare universal red cell stock (e.g. O-)
    if norm_donor == norm_recip:
        compat_score = exact_pts
        compat_reason = f"Exact blood match ({norm_donor} to {norm_recip})"
    else:
        compat_score = compat_pts
        compat_reason = f"Compatible alternative ({norm_donor} to {norm_recip})"

    # 2. Distance / Proximity Factor
    clamped_radius = max(max_radius_km, 1.0)
    dist_ratio = min(distance_km / clamped_radius, 1.0)
    distance_score = round(prox_weight * (1.0 - dist_ratio), 2)

    # 3. Reliability & Past Response Factor
    clamped_reliability = max(0.0, min(float(reliability_score or 1.0), 1.0))
    rel_score = round(rel_weight * clamped_reliability, 2)

    # 4. Donation Interval / Recency Buffer Factor
    interval_score = round(interval_weight * 0.5, 2)  # Default neutral for first-time donors
    if last_donation_date_str:
        try:
            parts = [int(p) for p in last_donation_date_str.split("-")]
            if len(parts) == 3:
                days = (date.today() - date(parts[0], parts[1], parts[2])).days
                if days > 180:
                    interval_score = interval_weight
                elif days > 120:
                    interval_score = round(interval_weight * 0.8, 2)
                elif days >= 90:
                    interval_score = round(interval_weight * 0.6, 2)
                else:
                    interval_score = 0.0
        except Exception:
            pass

    # 5. Intent Bonus
    intent_score = 0.0
    intent_label = donation_intent or "REGULAR"
    if intent_label == "REGULAR":
        intent_score = intent_reg_bonus
    elif intent_label == "WHEN_NEEDED":
        intent_score = intent_needed_bonus

    total_score = round(compat_score + distance_score + rel_score + interval_score + intent_score, 2)

    return {
        "total_score": total_score,
        "breakdown": {
            "compatibility_points": compat_score,
            "compatibility_reason": compat_reason,
            "proximity_points": distance_score,
            "distance_km": round(distance_km, 2),
            "reliability_points": rel_score,
            "interval_points": interval_score,
            "intent_points": intent_score,
            "intent_label": intent_label
        }
    }
