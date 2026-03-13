# =============================================================================
# Alternative Sourcing Service
# =============================================================================
# This module handles intelligent medicine sourcing across village pharmacies.
# 
# Key Features:
# 1. Find medicines in patient's local pharmacy
# 2. If out of stock, find nearest alternative village with stock
# 3. Generate prescription pickup SMS messages
# =============================================================================

from services.supabase_client import supabase

# =============================================================================
# VILLAGE PROXIMITY MAP (Nabha, Punjab Region)
# =============================================================================
# Approximate distances in kilometers between villages with pharmacies.
# Used to find the "next closest" alternative when medicine is out of stock.
#
# Geography: These villages surround Nabha Civil Hospital in Punjab.
# =============================================================================

VILLAGE_DISTANCES = {
    # From Bhadson to all other villages
    'Bhadson': {
        'Nabha': 8, 'Rohti': 5, 'Chondhi': 10, 'Kheri': 12, 
        'Amloh': 15, 'Patiala': 30, 'Malegaon': 35
    },
    # From Nabha (hospital location) to all other villages
    'Nabha': {
        'Bhadson': 8, 'Rohti': 6, 'Chondhi': 12, 'Kheri': 15,
        'Amloh': 18, 'Patiala': 25, 'Malegaon': 30
    },
    # From Rohti
    'Rohti': {
        'Bhadson': 5, 'Nabha': 6, 'Chondhi': 8, 'Kheri': 10,
        'Amloh': 12, 'Patiala': 28, 'Malegaon': 32
    },
    # From Chondhi
    'Chondhi': {
        'Bhadson': 10, 'Nabha': 12, 'Rohti': 8, 'Kheri': 6,
        'Amloh': 10, 'Patiala': 20, 'Malegaon': 25
    },
    # From Kheri
    'Kheri': {
        'Bhadson': 12, 'Nabha': 15, 'Rohti': 10, 'Chondhi': 6,
        'Amloh': 8, 'Patiala': 18, 'Malegaon': 22
    },
    # From Amloh
    'Amloh': {
        'Bhadson': 15, 'Nabha': 18, 'Rohti': 12, 'Chondhi': 10,
        'Kheri': 8, 'Patiala': 12, 'Malegaon': 20
    },
    # From Patiala (city)
    'Patiala': {
        'Bhadson': 30, 'Nabha': 25, 'Rohti': 28, 'Chondhi': 20,
        'Kheri': 18, 'Amloh': 12, 'Malegaon': 15
    },
    # From Malegaon
    'Malegaon': {
        'Bhadson': 35, 'Nabha': 30, 'Rohti': 32, 'Chondhi': 25,
        'Kheri': 22, 'Amloh': 20, 'Patiala': 15
    }
}


def get_distance(from_village: str, to_village: str) -> int:
    """Get distance between two villages in km. Returns 999 if unknown."""
    if from_village == to_village:
        return 0
    return VILLAGE_DISTANCES.get(from_village, {}).get(to_village, 999)


def find_medicine_availability(medicine_name: str, patient_village: str) -> dict:
    """
    Find where a medicine is available, prioritizing patient's village.
    
    Returns:
    {
        'found': bool,
        'pharmacy_name': str,
        'pharmacy_village': str,
        'is_local': bool,          # True if in patient's village
        'distance_km': int,         # Distance from patient's village
        'alternative_reason': str   # Why alternative was needed (if not local)
    }
    """
    # Normalize medicine name for searching (case-insensitive partial match)
    search_term = medicine_name.strip().lower()
    
    # Step 1: Get all pharmacies with this medicine in stock
    # We search for medicines where name contains the search term
    result = supabase.table('medicines') \
        .select('*, pharmacies(id, name, village)') \
        .ilike('medicine_name', f'%{search_term}%') \
        .eq('is_in_stock', True) \
        .execute()
    
    if not result.data:
        # Medicine not found anywhere
        return {
            'found': False,
            'pharmacy_name': None,
            'pharmacy_village': None,
            'is_local': False,
            'distance_km': None,
            'alternative_reason': 'Medicine not available in any pharmacy'
        }
    
    # Step 2: Check if available in patient's village
    for med in result.data:
        pharmacy = med.get('pharmacies', {})
        if pharmacy and pharmacy.get('village', '').lower() == patient_village.lower():
            return {
                'found': True,
                'pharmacy_name': pharmacy.get('name'),
                'pharmacy_village': pharmacy.get('village'),
                'is_local': True,
                'distance_km': 0,
                'alternative_reason': None
            }
    
    # Step 3: Find nearest alternative village with stock
    alternatives = []
    for med in result.data:
        pharmacy = med.get('pharmacies', {})
        if pharmacy:
            village = pharmacy.get('village')
            distance = get_distance(patient_village, village)
            alternatives.append({
                'pharmacy_name': pharmacy.get('name'),
                'pharmacy_village': village,
                'distance_km': distance
            })
    
    # Sort by distance and pick the closest
    alternatives.sort(key=lambda x: x['distance_km'])
    
    if alternatives:
        best = alternatives[0]
        return {
            'found': True,
            'pharmacy_name': best['pharmacy_name'],
            'pharmacy_village': best['pharmacy_village'],
            'is_local': False,
            'distance_km': best['distance_km'],
            'alternative_reason': f"Out of stock in {patient_village}"
        }
    
    return {
        'found': False,
        'pharmacy_name': None,
        'pharmacy_village': None,
        'is_local': False,
        'distance_km': None,
        'alternative_reason': 'No pharmacies found with this medicine'
    }


def find_all_alternatives(medicine_name: str, patient_village: str, limit: int = 3) -> list:
    """
    Find all alternative pharmacies with the medicine, sorted by distance.
    Used for showing multiple options on the doctor dashboard.
    
    Returns list of:
    {
        'pharmacy_name': str,
        'pharmacy_village': str,
        'distance_km': int,
        'is_local': bool
    }
    """
    search_term = medicine_name.strip().lower()
    
    result = supabase.table('medicines') \
        .select('*, pharmacies(id, name, village)') \
        .ilike('medicine_name', f'%{search_term}%') \
        .eq('is_in_stock', True) \
        .execute()
    
    if not result.data:
        return []
    
    alternatives = []
    for med in result.data:
        pharmacy = med.get('pharmacies', {})
        if pharmacy:
            village = pharmacy.get('village')
            distance = get_distance(patient_village, village)
            alternatives.append({
                'pharmacy_name': pharmacy.get('name'),
                'pharmacy_village': village,
                'distance_km': distance,
                'is_local': village.lower() == patient_village.lower()
            })
    
    # Sort by distance
    alternatives.sort(key=lambda x: x['distance_km'])
    
    return alternatives[:limit]


def generate_prescription_sms(patient_name: str, prescription: str, availability: dict) -> str:
    """
    Generate a patient-friendly SMS message for prescription pickup.
    Designed for basic Nokia phones (no fancy formatting, short text).
    """
    # Extract first medicine from prescription (often comma/semicolon separated)
    first_med = prescription.split(',')[0].split(';')[0].strip()
    
    if not availability['found']:
        return (
            f"Namaste {patient_name}, your prescription is ready. "
            f"Medicine: {first_med}. "
            f"Please visit Nabha Civil Hospital pharmacy. "
            f"- SehatSetu"
        )
    
    if availability['is_local']:
        return (
            f"Namaste {patient_name}, your prescription is ready.\n"
            f"Medicine: {first_med}\n"
            f"Pickup: {availability['pharmacy_name']}, {availability['pharmacy_village']}\n"
            f"- SehatSetu"
        )
    else:
        return (
            f"Namaste {patient_name}, your prescription is ready.\n"
            f"Medicine: {first_med}\n"
            f"NOTE: Out of stock locally.\n"
            f"Available at: {availability['pharmacy_name']}, {availability['pharmacy_village']} ({availability['distance_km']}km)\n"
            f"- SehatSetu"
        )


def check_prescription_availability(prescription: str, patient_village: str) -> dict:
    """
    Check availability for all medicines in a prescription.
    Returns aggregated availability info.
    """
    # Split prescription into individual medicines
    # Handle common separators: comma, semicolon, newline
    import re
    medicines = re.split(r'[,;\n]+', prescription)
    medicines = [m.strip() for m in medicines if m.strip()]
    
    results = []
    all_available_locally = True
    any_found = False
    
    for med in medicines:
        # Skip common prescription words that aren't medicines
        if len(med) < 3 or med.lower() in ['mg', 'ml', 'tablet', 'tablets', 'syrup', 'dose', 'daily', 'twice', 'once']:
            continue
            
        availability = find_medicine_availability(med, patient_village)
        if availability['found']:
            any_found = True
            if not availability['is_local']:
                all_available_locally = False
        results.append({
            'medicine': med,
            **availability
        })
    
    return {
        'medicines': results,
        'all_local': all_available_locally,
        'any_found': any_found,
        'patient_village': patient_village
    }
