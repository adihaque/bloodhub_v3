"""
Centralized state-machine validators for BloodRequest and DonorProfile.
Prevents arbitrary or invalid transitions.
"""

class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass

class RequestStateMachine:
    VALID_STATES = {
        "DRAFT", "SCHEDULED", "ACTIVE", "MATCHING",
        "AWAITING_DONOR", "ASSIGNED", "CONFIRMED",
        "COMPLETED", "CANCELLED", "EXPIRED", "UNFULFILLED"
    }

    ALLOWED_TRANSITIONS = {
        "DRAFT": {"ACTIVE", "CANCELLED"},
        "SCHEDULED": {"ACTIVE", "CANCELLED"},
        "ACTIVE": {"MATCHING", "CANCELLED", "EXPIRED"},
        "MATCHING": {"AWAITING_DONOR", "ASSIGNED", "UNFULFILLED", "CANCELLED", "EXPIRED"},
        "AWAITING_DONOR": {"ASSIGNED", "MATCHING", "UNFULFILLED", "CANCELLED", "EXPIRED"},
        "ASSIGNED": {"CONFIRMED", "MATCHING", "CANCELLED"},
        "CONFIRMED": {"COMPLETED", "CANCELLED"},
        "COMPLETED": set(),     # Terminal state
        "CANCELLED": set(),     # Terminal state
        "EXPIRED": set(),       # Terminal state
        "UNFULFILLED": set(),   # Terminal state
    }

    @classmethod
    def validate_transition(cls, current_state: str, new_state: str) -> None:
        if new_state not in cls.VALID_STATES:
            raise StateTransitionError(f"Target state '{new_state}' is not a valid BloodRequest state.")
        if current_state == new_state:
            return  # Idempotent state assignment
        allowed = cls.ALLOWED_TRANSITIONS.get(current_state, set())
        if new_state not in allowed:
            raise StateTransitionError(
                f"Invalid request transition from '{current_state}' to '{new_state}'. Allowed: {sorted(list(allowed))}"
            )

class DonorStateMachine:
    VALID_STATES = {
        "ACTIVE", "AVAILABLE", "UNAVAILABLE",
        "OFFERED", "ASSIGNED", "RESTRICTED", "SUSPENDED"
    }

    ALLOWED_TRANSITIONS = {
        "AVAILABLE": {"UNAVAILABLE", "OFFERED", "ASSIGNED", "RESTRICTED", "SUSPENDED"},
        "UNAVAILABLE": {"AVAILABLE", "RESTRICTED", "SUSPENDED"},
        "OFFERED": {"AVAILABLE", "ASSIGNED", "UNAVAILABLE", "RESTRICTED", "SUSPENDED"},
        "ASSIGNED": {"AVAILABLE", "UNAVAILABLE", "RESTRICTED", "SUSPENDED"},
        "RESTRICTED": {"AVAILABLE", "UNAVAILABLE", "SUSPENDED"},
        "SUSPENDED": {"AVAILABLE", "UNAVAILABLE"},
        "ACTIVE": {"AVAILABLE", "UNAVAILABLE", "RESTRICTED", "SUSPENDED"}
    }

    @classmethod
    def validate_transition(cls, current_state: str, new_state: str) -> None:
        if new_state not in cls.VALID_STATES:
            raise StateTransitionError(f"Target state '{new_state}' is not a valid Donor state.")
        if current_state == new_state:
            return
        allowed = cls.ALLOWED_TRANSITIONS.get(current_state, set())
        if new_state not in allowed:
            raise StateTransitionError(
                f"Invalid donor transition from '{current_state}' to '{new_state}'. Allowed: {sorted(list(allowed))}"
            )
