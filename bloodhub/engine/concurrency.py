import threading
from datetime import datetime
from typing import Dict, Any
from bloodhub.core.database import DatabaseSession
from bloodhub.models.models import BloodRequest, DonorOffer, DonorProfile, Assignment, User, AuditLog
from bloodhub.domain.state_machines import RequestStateMachine, DonorStateMachine
from bloodhub.providers.notifications.console import ConsoleNotificationProvider

notification_provider = ConsoleNotificationProvider()

# Global re-entrant lock for thread safety in multi-threaded environments / SQLite
_concurrency_mutex = threading.RLock()

def atomic_accept_offer(db: DatabaseSession, offer_id: str, donor_id: str) -> Dict[str, Any]:
    """
    Atomically processes a donor's acceptance of an incoming dispatch offer.
    Guarantees strict concurrency control: only one donor can claim an available unit.
    All competing simultaneous requests are safely serialized and rejected.
    """
    with _concurrency_mutex:
        try:
            # 1. Fetch offer
            offer = db.query(DonorOffer).filter(
                "id = ? AND donor_id = ?", [offer_id, donor_id]
            ).first()

            if not offer:
                return {
                    "success": False,
                    "code": "OFFER_NOT_FOUND",
                    "message": "Offer does not exist or does not belong to this donor."
                }

            if offer.status != "OFFERED":
                return {
                    "success": False,
                    "code": "OFFER_INVALID_STATE",
                    "message": f"Offer is already in state '{offer.status}'."
                }

            # 2. Lock and inspect BloodRequest
            request = db.query(BloodRequest).filter_by(id=offer.request_id).first()
            if not request:
                return {
                    "success": False,
                    "code": "REQUEST_NOT_FOUND",
                    "message": "Associated blood request not found."
                }

            # Check if request can accept another donor
            if request.status in ("ASSIGNED", "CONFIRMED", "COMPLETED", "CANCELLED", "EXPIRED"):
                offer.status = "REVOKED"
                db.add(offer)
                db.commit()
                return {
                    "success": False,
                    "code": "REQUEST_ALREADY_FULFILLED",
                    "message": "Another donor accepted this emergency request just moments before you. Thank you for your readiness!"
                }

            if int(request.units_fulfilled or 0) >= int(request.units_needed or 1):
                offer.status = "REVOKED"
                db.add(offer)
                db.commit()
                return {
                    "success": False,
                    "code": "ALL_UNITS_CLAIMED",
                    "message": "All required units for this request have already been assigned."
                }

            # Check offer expiration
            now = datetime.utcnow()
            offer_exp = datetime.fromisoformat(offer.expires_at) if isinstance(offer.expires_at, str) else offer.expires_at
            if offer_exp < now:
                offer.status = "TIMED_OUT"
                db.add(offer)
                db.commit()
                return {
                    "success": False,
                    "code": "OFFER_EXPIRED",
                    "message": "This offer has expired."
                }

            # 3. Winning Donor: Atomic Lock & Transition
            offer.status = "ACCEPTED"
            offer.responded_at = now.isoformat()
            db.add(offer)

            request.units_fulfilled = int(request.units_fulfilled or 0) + 1
            if int(request.units_fulfilled or 0) >= int(request.units_needed or 1):
                RequestStateMachine.validate_transition(request.status, "ASSIGNED")
                request.status = "ASSIGNED"
            db.add(request)

            # 4. Create Assignment Record
            assignment = Assignment(
                request_id=request.id,
                donor_id=donor_id,
                offer_id=offer.id,
                status="ACTIVE",
                assigned_at=now.isoformat()
            )
            db.add(assignment)
            db.flush()

            # 5. Update Donor Profile
            donor_profile = db.query(DonorProfile).filter_by(user_id=donor_id).first()
            if donor_profile:
                DonorStateMachine.validate_transition(donor_profile.availability_status, "ASSIGNED")
                donor_profile.availability_status = "ASSIGNED"
                donor_profile.active_assignment_id = assignment.id
                donor_profile.accepted_count = int(donor_profile.accepted_count or 0) + 1
                db.add(donor_profile)

            # 6. Revoke competing offers for this request if fully assigned
            if request.status == "ASSIGNED":
                competing_offers = db.query(DonorOffer).filter(
                    "request_id = ? AND id != ? AND status = 'OFFERED'",
                    [request.id, offer.id]
                ).all()

                for comp_offer in competing_offers:
                    comp_offer.status = "REVOKED"
                    db.add(comp_offer)
                    comp_donor = db.query(DonorProfile).filter_by(user_id=comp_offer.donor_id).first()
                    if comp_donor and comp_donor.availability_status == "OFFERED":
                        comp_donor.availability_status = "AVAILABLE"
                        db.add(comp_donor)

            # 7. Audit Log
            audit = AuditLog(
                user_id=donor_id,
                action="OFFER_ACCEPTED_ATOMICALLY",
                resource_type="Assignment",
                resource_id=assignment.id,
                details=f"Donor {donor_id} locked assignment for request {request.id} ({request.blood_group} at {request.hospital_name})."
            )
            db.add(audit)

            db.commit()
            db.refresh(assignment)

            # 8. Notify Requester
            donor_user = db.query(User).filter_by(id=donor_id).first()
            if donor_user:
                notification_provider.send_assignment_confirmation(
                    request.contact_phone,
                    {
                        "name": donor_user.full_name,
                        "blood_group": donor_profile.blood_group if donor_profile else request.blood_group,
                        "phone": donor_user.phone
                    }
                )

            return {
                "success": True,
                "code": "ASSIGNED_SUCCESS",
                "assignment_id": assignment.id,
                "request_id": request.id,
                "message": "Emergency assignment successfully locked. Please proceed to the medical facility."
            }

        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "code": "TRANSACTION_ERROR",
                "message": f"Database transaction failed: {str(e)}"
            }
