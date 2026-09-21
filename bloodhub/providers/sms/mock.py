import logging
from bloodhub.providers.sms.base import SmsProvider

logger = logging.getLogger("bloodhub.sms")

class MockSmsProvider(SmsProvider):
    def send_sms(self, phone: str, message: str) -> bool:
        print(f"\n📱 [SMS OUTBOUND -> {phone}]: {message}")
        return True
