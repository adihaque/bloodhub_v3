"""Twilio/WhatsApp contract. It is intentionally a no-op until configured."""
from bloodhub.providers.sms.base import SmsProvider

class TwilioProvider(SmsProvider):
    def __init__(self, account_sid: str = "", auth_token: str = "", from_number: str = ""):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number

    def send_sms(self, phone: str, message: str) -> bool:
        # Integrators can replace this adapter without changing dispatch code.
        return True
