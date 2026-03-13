from flask import Blueprint, request, jsonify
from services.supabase_client import supabase
from services.twilio_service import send_sms
from services.sourcing_service import (
    find_medicine_availability,
    find_all_alternatives,
    generate_prescription_sms,
    check_prescription_availability
)

consultations_bp = Blueprint('consultations', __name__)


@consultations_bp.route('/api/consultations', methods=['GET'])
def list_consultations():
    """List consultations sorted by priority (RED→YELLOW→GREEN) then timestamp."""
    status_filter = request.args.get('status', 'Pending')

    result = supabase.table('consultations') \
        .select('*, patients(name, phone, village, age, gender)') \
        .eq('status', status_filter) \
        .order('created_at', desc=True) \
        .execute()

    # Sort by priority: RED first, then YELLOW, then GREEN
    priority_order = {'RED': 0, 'YELLOW': 1, 'GREEN': 2}
    sorted_data = sorted(
        result.data,
        key=lambda c: (priority_order.get(c.get('ai_priority', 'YELLOW'), 1), c.get('created_at', ''))
    )

    return jsonify(sorted_data)


@consultations_bp.route('/api/consultations/<consultation_id>', methods=['PATCH'])
def update_consultation(consultation_id):
    """
    Update doctor notes, prescription, or mark as resolved.
    
    When resolved with a prescription:
    1. Checks medicine availability in patient's village
    2. Finds nearest alternative if out of stock locally
    3. Sends SMS to patient with pickup instructions
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    update_fields = {}
    if 'doctor_notes' in data:
        update_fields['doctor_notes'] = data['doctor_notes']
    if 'prescription' in data:
        update_fields['prescription'] = data['prescription']
    if 'status' in data:
        update_fields['status'] = data['status']

    if not update_fields:
        return jsonify({"error": "No valid fields to update"}), 400

    # Update the consultation
    result = supabase.table('consultations') \
        .update(update_fields) \
        .eq('id', consultation_id) \
        .execute()

    if not result.data:
        return jsonify({"error": "Not found"}), 404

    consultation = result.data[0]

    # =========================================================================
    # AUTO-SMS ON RESOLVE: Send prescription pickup SMS to patient
    # =========================================================================
    if data.get('status') == 'Resolved' and consultation.get('prescription'):
        try:
            # Fetch patient info for SMS
            patient_id = consultation.get('patient_id')
            patient_result = supabase.table('patients') \
                .select('name, phone, village') \
                .eq('id', patient_id) \
                .execute()

            if patient_result.data:
                patient = patient_result.data[0]
                patient_name = patient.get('name', 'Patient')
                patient_phone = patient.get('phone')
                patient_village = patient.get('village', 'Nabha')

                if patient_phone:
                    # Check medicine availability with alternative sourcing
                    prescription = consultation.get('prescription', '')
                    
                    # Get first medicine from prescription for availability check
                    first_med = prescription.split(',')[0].split(';')[0].strip()
                    availability = find_medicine_availability(first_med, patient_village)

                    # Generate and send SMS
                    sms_message = generate_prescription_sms(
                        patient_name=patient_name,
                        prescription=prescription,
                        availability=availability
                    )

                    # Format phone number for Twilio (add +91 if needed)
                    phone = patient_phone.strip()
                    if not phone.startswith('+'):
                        phone = '+91' + phone.lstrip('0')

                    sms_sid = send_sms(phone, sms_message)
                    
                    # Add SMS info to response
                    consultation['_sms_sent'] = bool(sms_sid)
                    consultation['_sms_message'] = sms_message
                    consultation['_availability'] = availability

                    print(f"[Resolve SMS] Sent to {phone}: {sms_message[:50]}...")

        except Exception as e:
            print(f"[Resolve SMS Error] {e}")
            consultation['_sms_error'] = str(e)

    return jsonify(consultation)


@consultations_bp.route('/api/consultations/check-availability', methods=['POST'])
def check_availability():
    """
    Check medicine availability for a prescription.
    Used by doctor dashboard to show availability before resolving.
    
    Request body:
    {
        "prescription": "Paracetamol, Azithromycin",
        "village": "Bhadson"
    }
    
    Returns availability info with alternatives for each medicine.
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    prescription = data.get('prescription', '')
    village = data.get('village', 'Nabha')
    
    if not prescription:
        return jsonify({"error": "prescription field required"}), 400
    
    result = check_prescription_availability(prescription, village)
    return jsonify(result)


@consultations_bp.route('/api/consultations/find-alternatives', methods=['GET'])
def find_alternatives():
    """
    Find alternative pharmacies for a specific medicine.
    
    Query params:
    - medicine: Medicine name to search
    - village: Patient's village (for distance calculation)
    - limit: Max alternatives to return (default 3)
    
    Returns list of pharmacies with the medicine in stock, sorted by distance.
    """
    medicine = request.args.get('medicine', '')
    village = request.args.get('village', 'Nabha')
    limit = int(request.args.get('limit', 3))
    
    if not medicine:
        return jsonify({"error": "medicine parameter required"}), 400
    
    alternatives = find_all_alternatives(medicine, village, limit)
    return jsonify({
        'medicine': medicine,
        'patient_village': village,
        'alternatives': alternatives
    })
