import urllib.parse
from typing import Dict, Any, List, Optional
from datetime import datetime
from bloodhub.providers.notifications.base import NotificationProvider

def _safe_print(message: str) -> None:
    """Keep console notifications usable on Windows terminals without UTF-8."""
    try:
        print(message)
    except UnicodeEncodeError:
        encoding = getattr(__import__("sys").stdout, "encoding", None) or "utf-8"
        print(message.encode(encoding, errors="replace").decode(encoding))

def clean_phone_for_whatsapp(phone: str) -> str:
    """Standardizes Bangladeshi phone number to international WhatsApp format without '+' or spaces."""
    if not phone:
        return "8801700000000"
    digits = "".join([c for c in phone if c.isdigit()])
    if digits.startswith("880"):
        return digits
    elif digits.startswith("0"):
        return "88" + digits
    return "880" + digits

class MultiChannelNotificationProvider(NotificationProvider):
    def __init__(self, base_app_url: str = "http://localhost:8000"):
        self.base_app_url = base_app_url

    def build_whatsapp_offer_message(
        self,
        donor_name: str,
        blood_group: str,
        component: str,
        hospital_name: str,
        hospital_address: str,
        distance_km: float,
        timeout_seconds: int,
        offer_id: str,
        patient_name: str = "Urgent Patient"
    ) -> str:
        app_link = f"{self.base_app_url}/donor?offer_id={offer_id}"
        msg = (
            f"🚨 *BLOOD HUB BANGLADESH — EMERGENCY CALL* 🚨\n\n"
            f"Dear {donor_name},\n"
            f"A patient urgently requires *{blood_group}* ({component or 'Whole Blood'}).\n\n"
            f"🏥 *Hospital:* {hospital_name}\n"
            f"📍 *Location:* {hospital_address or 'Dhaka'}\n"
            f"📏 *Distance:* ~{round(distance_km, 1)} km from your area\n"
            f"⏱️ *Urgency:* Immediate response requested ({timeout_seconds}s window)\n\n"
            f"Can you donate and save a life today?\n"
            f"👉 *Tap here to Accept or Review:* {app_link}\n\n"
            f"_Blood Hub Volunteer Network • Reply directly if you have any questions._"
        )
        return msg

    def build_whatsapp_link(self, phone_or_wa: str, message_text: str) -> str:
        clean_num = clean_phone_for_whatsapp(phone_or_wa)
        encoded_text = urllib.parse.quote(message_text)
        return f"https://wa.me/{clean_num}?text={encoded_text}"

    def send_dispatch_offer(self, donor_id: str, offer_details: Dict[str, Any]) -> Dict[str, Any]:
        blood_group = offer_details.get("blood_group", "Blood")
        hospital_name = offer_details.get("hospital_name", "Hospital")
        distance_km = float(offer_details.get("distance_km") or 0.0)
        timeout_seconds = int(offer_details.get("timeout_seconds") or 25)
        donor_name = offer_details.get("donor_name", "Donor")
        donor_phone = offer_details.get("donor_phone", "")
        whatsapp_num = offer_details.get("whatsapp_number") or donor_phone
        offer_id = offer_details.get("offer_id", "")
        patient_name = offer_details.get("patient_name", "Emergency Patient")
        component = offer_details.get("component", "Whole Blood")

        # 1. WhatsApp link
        wa_text = self.build_whatsapp_offer_message(
            donor_name=donor_name,
            blood_group=blood_group,
            component=component,
            hospital_name=hospital_name,
            hospital_address=offer_details.get("hospital_address", "Dhaka"),
            distance_km=distance_km,
            timeout_seconds=timeout_seconds,
            offer_id=offer_id,
            patient_name=patient_name
        )
        wa_url = self.build_whatsapp_link(whatsapp_num, wa_text) if whatsapp_num else None

        # 2. In-App Call Alert Log
        _safe_print(f"\n📢 [PUSH / CALL-ALERT TO DONOR {donor_id}] Urgent Request: {blood_group} needed at {hospital_name}! Distance: {distance_km:.3f}km. Timeout: {timeout_seconds}s.")

        # 3. WhatsApp Dispatch Log
        if wa_url:
            _safe_print(f"💬 [WHATSAPP DISPATCH] To {whatsapp_num} -> {wa_url}")

        # 4. SMS Dispatch Log
        sms_text = f"[Blood Hub] URGENT: {blood_group} needed at {hospital_name} (~{distance_km:.1f}km). Open: {self.base_app_url}/donor"
        _safe_print(f"📱 [SMS DISPATCH] To {donor_phone} -> {sms_text}")

        return {
            "in_app": True,
            "whatsapp_url": wa_url,
            "sms_sent": True,
            "dispatched_at": datetime.utcnow().isoformat()
        }

    def send_assignment_confirmation(self, recipient_phone: str, donor_details: Dict[str, Any]) -> bool:
        donor_name = donor_details.get("name", "Donor")
        donor_blood = donor_details.get("blood_group", "")
        donor_phone = donor_details.get("phone", "")
        donor_wa = donor_details.get("whatsapp_number") or donor_phone

        _safe_print(f"\n🎉 [SMS TO REQUESTER {recipient_phone}] Donor Found! {donor_name} ({donor_blood}) has accepted and is en route. Contact: {donor_phone}")
        return True

    def send_request_cancellation(self, donor_ids: List[str], request_id: str) -> bool:
        _safe_print(f"\nℹ️ [CANCEL ALERT] Blood Request {request_id} has been cancelled. Alerted {len(donor_ids)} donors.")
        return True

class ConsoleNotificationProvider(MultiChannelNotificationProvider):
    pass
