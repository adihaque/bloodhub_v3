"""FCM contract with a safe mock implementation; credentials are never required locally."""
from typing import Any, Dict
from bloodhub.providers.notifications.base import NotificationProvider

class FcmProvider(NotificationProvider):
    def __init__(self, project_id: str = "", credentials_json: str = ""):
        self.project_id = project_id
        self.credentials_json = credentials_json

    def send_dispatch_offer(self, donor_id: str, offer_details: Dict[str, Any]) -> bool:
        return True

    def send_assignment_confirmation(self, recipient_phone: str, donor_details: Dict[str, Any]) -> bool:
        return True

    def send_request_cancellation(self, donor_ids, request_id: str) -> bool:
        return True
