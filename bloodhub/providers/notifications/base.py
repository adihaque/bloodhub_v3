from abc import ABC, abstractmethod
from typing import Dict, Any, List

class NotificationProvider(ABC):
    @abstractmethod
    def send_dispatch_offer(self, donor_id: str, offer_details: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def send_assignment_confirmation(self, recipient_phone: str, donor_details: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def send_request_cancellation(self, donor_ids: List[str], request_id: str) -> bool:
        pass
