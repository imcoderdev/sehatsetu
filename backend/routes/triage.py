from flask import Blueprint, request, jsonify
from services.supabase_client import supabase
from services.gemini_service import triage_patient

triage_bp = Blueprint('triage', __name__)


@triage_bp.route('/api/triage', methods=['POST'])
def triage():
    """Receive patient data, store in DB, run AI triage."""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    village = data.get('village', '').strip()
    age = data.get('age')
    gender = data.get('gender', '').strip() or None
    symptoms = data.get('symptoms', '').strip()

    if not name or not symptoms:
        return jsonify({"error": "Name and symptoms are required"}), 400

    try:
        # 1. Insert or find patient
        patient_result = supabase.table('patients').insert({
            "name": name,
            "phone": phone,
            "village": village,
            "age": int(age) if age else None,
            "gender": gender
        }).execute()

        patient = patient_result.data[0]

        # 2. Run AI triage
        ai_result = triage_patient(name, age, village, symptoms)

        # 3. Store consultation
        consultation_result = supabase.table('consultations').insert({
            "patient_id": patient['id'],
            "raw_symptoms": symptoms,
            "ai_priority": ai_result['priority'],
            "ai_summary": ai_result['summary'],
            "source": data.get('source', 'app')
        }).execute()

        consultation = consultation_result.data[0]

        return jsonify({
            "success": True,
            "patient_id": patient['id'],
            "consultation_id": consultation['id'],
            "priority": ai_result['priority'],
            "summary": ai_result['summary']
        }), 201

    except Exception as e:
        print(f"[Triage Error] {e}")
        return jsonify({"error": str(e)}), 500
