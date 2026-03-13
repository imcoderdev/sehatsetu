from flask import Blueprint, request, jsonify
from services.supabase_client import supabase

pharmacy_bp = Blueprint('pharmacy', __name__)


@pharmacy_bp.route('/api/pharmacy/medicines', methods=['GET'])
def list_medicines():
    """List medicines, optionally filtered by village."""
    village = request.args.get('village')

    if village:
        # Village-based lookup: Patient → Village → Pharmacy → Medicines
        pharmacy_result = supabase.table('pharmacies') \
            .select('id') \
            .ilike('village', village) \
            .execute()

        if not pharmacy_result.data:
            return jsonify([])

        pharmacy_id = pharmacy_result.data[0]['id']
        result = supabase.table('medicines') \
            .select('*, pharmacies(name, village)') \
            .eq('pharmacy_id', pharmacy_id) \
            .order('medicine_name') \
            .execute()
    else:
        result = supabase.table('medicines') \
            .select('*, pharmacies(name, village)') \
            .order('medicine_name') \
            .execute()

    return jsonify(result.data)


@pharmacy_bp.route('/api/pharmacy/medicines/<medicine_id>', methods=['PATCH'])
def toggle_stock(medicine_id):
    """Toggle medicine stock status."""
    data = request.get_json()

    if data is None or 'is_in_stock' not in data:
        return jsonify({"error": "is_in_stock field required"}), 400

    result = supabase.table('medicines') \
        .update({"is_in_stock": data['is_in_stock']}) \
        .eq('id', medicine_id) \
        .execute()

    return jsonify(result.data[0] if result.data else {"error": "Not found"})
