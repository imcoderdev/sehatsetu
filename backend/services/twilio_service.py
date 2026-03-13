from twilio.rest import Client
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_MESSAGING_SID

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def send_sms(to_number, message):
    """Send an SMS reply via Twilio."""
    try:
        msg = twilio_client.messages.create(
            to=to_number,
            messaging_service_sid=TWILIO_MESSAGING_SID,
            body=message
        )
        print(f"[Twilio] SMS sent to {to_number}: {msg.sid}")
        return msg.sid
    except Exception as e:
        print(f"[Twilio Error] {e}")
        return None
