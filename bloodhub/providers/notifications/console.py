import logging
from typing import Dict, Any, List
from bloodhub.providers.notifications.base import NotificationProvider

logger = logging.getLogger("bloodhub.notifications")

class ConsoleNotificationProvider(NotificationProvider):
    def send_dispatch_offer(self, donor_id: str, offer_details: Dict[str, Any]) -> bool:
        print(f"\n📢 [PUSH / CALL-ALERT TO DONOR {donor_id}] Urgent Request: {offer_details.get('blood_group')} needed at {offer_details.get('hospital_name')}! Distance: {offer_details.get('distance_km')}km. Timeout: {offer_details.get('timeout_seconds')}s.")
        return True

    def send_assignment_confirmation(self, recipient_phone: str, donor_details: Dict[str, Any]) -> bool:
        print(f"\n🎉 [SMS TO REQUESTER {recipient_phone}] Donor Found! {donor_details.get('name')} ({donor_details.get('blood_group')}) has accepted and is en route. Contact: {donor_details.get('phone')}")
        return True

    def send_request_cancellation(self, donor_ids: List[str], request_id: str) -> bool:
        print(f"\nℹ️ [CANCEL ALERT] Blood Request {request_id} has been cancelled. Alerted {len(donor_ids)} donors.")
        return True
