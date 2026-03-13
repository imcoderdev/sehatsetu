import re
from flask import Blueprint, request, Response
from services.supabase_client import supabase
from services.gemini_service import triage_patient
from services.twilio_service import send_sms

sms_bp = Blueprint('sms', __name__)

KEYWORD = "SEHAT"

# SMS format: SEHAT <symptoms>
# Example: "SEHAT CHEST PAIN CANT BREATHE"
# Also accepts raw symptoms without keyword for convenience

HELP_REPLY = (
    "SehatSetu SMS Triage\n"
    "Send: SEHAT followed by symptoms\n"
    "Example: SEHAT CHEST PAIN CANT BREATHE\n"
    "We will connect you with a doctor."
)


@sms_bp.route('/api/sms-webhook', methods=['POST'])
def sms_webhook():
    """Receive incoming SMS from Twilio, extract symptoms, run AI triage, auto-reply."""
    body = request.form.get('Body', '').strip()
    from_number = request.form.get('From', '').strip()

    print(f"[SMS] Incoming from {from_number}: {body}")

    if not body or not from_number:
        return twiml_response("We could not process your message. Please try again.")

    # Extract symptoms: remove SEHAT keyword if present
    symptoms = re.sub(r'^SEHAT\s*', '', body, flags=re.IGNORECASE).strip()

    if not symptoms:
        return twiml_response(HELP_REPLY)

    try:
        # 1. Check if patient exists by phone number, else create
        existing = supabase.table('patients').select('*').eq('phone', from_number).execute()

        if existing.data:
            patient = existing.data[0]
            print(f"[SMS] Found existing patient: {patient['name']}")
        else:
            patient_result = supabase.table('patients').insert({
                "name": f"SMS Patient ({from_number[-4:]})",
                "phone": from_number,
                "village": "Unknown (SMS)"
            }).execute()
            patient = patient_result.data[0]
            print(f"[SMS] Created new patient: {patient['name']}")

        # 2. Run Groq AI triage
        print(f"[SMS] Running AI triage for: {symptoms}")
        ai_result = triage_patient(
            name=patient['name'],
            age=patient.get('age', 'Unknown'),
            village=patient.get('village', 'Unknown'),
            symptoms=symptoms
        )
        print(f"[SMS] Triage result: {ai_result['priority']} - {ai_result['summary']}")

        # 3. Store consultation
        supabase.table('consultations').insert({
            "patient_id": patient['id'],
            "raw_symptoms": symptoms,
            "ai_priority": ai_result['priority'],
            "ai_summary": ai_result['summary'],
            "source": "sms"
        }).execute()

        # 4. Build priority-based reply
        priority = ai_result['priority']

        if priority == 'RED':
            reply = (
                "URGENT: Your symptoms indicate a possible emergency.\n"
                "You have been added to the Doctor Queue as HIGH PRIORITY.\n"
                "Expect a call within 10 mins.\n"
                "If symptoms worsen, go to the nearest hospital IMMEDIATELY."
            )
        elif priority == 'YELLOW':
            reply = (
                "Your symptoms have been reviewed by our AI system.\n"
                "You have been added to the Doctor Queue as MODERATE priority.\n"
                "A doctor will call you soon.\n"
                "If symptoms worsen, send another SMS or visit the hospital."
            )
        else:
            reply = (
                "Your symptoms have been noted.\n"
                "A doctor will review your case and may call you.\n"
                "If symptoms worsen, send: SEHAT followed by updated symptoms."
            )

        print(f"[SMS] Replying to {from_number} with {priority} response")
        return twiml_response(reply)

    except Exception as e:
        print(f"[SMS Webhook Error] {e}")
        return twiml_response(
            "We received your message. A healthcare worker will contact you soon.\n"
            "If this is an emergency, please go to the nearest hospital."
        )


def twiml_response(message):
    """Helper to build TwiML XML response for Twilio."""
    from xml.sax.saxutils import escape
    safe_message = escape(message)
    twiml = '<?xml version="1.0" encoding="UTF-8"?>'
    twiml += f'<Response><Message>{safe_message}</Message></Response>'
    return Response(twiml, mimetype='text/xml')
