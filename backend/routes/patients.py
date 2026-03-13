from flask import Blueprint, request, jsonify
from services.supabase_client import supabase

patients_bp = Blueprint('patients', __name__)


@patients_bp.route('/api/patients', methods=['GET'])
def list_patients():
    """List all patients, optionally filtered by village."""
    village = request.args.get('village')

    query = supabase.table('patients').select('*').order('created_at', desc=True)

    if village:
        query = query.eq('village', village)

    result = query.execute()
    return jsonify(result.data)


@patients_bp.route('/api/patients/<patient_id>/history', methods=['GET'])
def patient_history(patient_id):
    """Get patient details + consultation history."""
    patient = supabase.table('patients').select('*').eq('id', patient_id).single().execute()

    consultations = supabase.table('consultations') \
        .select('*') \
        .eq('patient_id', patient_id) \
        .order('created_at', desc=True) \
        .execute()

    return jsonify({
        "patient": patient.data,
        "consultations": consultations.data
    })
