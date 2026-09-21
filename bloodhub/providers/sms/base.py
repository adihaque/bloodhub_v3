from abc import ABC, abstractmethod

class SmsProvider(ABC):
    @abstractmethod
    def send_sms(self, phone: str, message: str) -> bool:
        pass
