# =============================================================================
# TTS Route — Text-to-Speech using espeak-ng
# =============================================================================
# This endpoint provides OFFLINE Punjabi text-to-speech using espeak-ng.
# espeak-ng is an open-source speech synthesizer with Punjabi support.
# 
# Installation: winget install eSpeak-NG.eSpeak-NG
# =============================================================================

import os
import subprocess
import tempfile
from flask import Blueprint, request, send_file, jsonify

tts_bp = Blueprint('tts', __name__)

# Path to espeak-ng executable (default Windows install location)
ESPEAK_PATH = r"C:\Program Files\eSpeak NG\espeak-ng.exe"

# Predefined instructions for Read Aloud (to avoid passing long text via URL)
INSTRUCTIONS = {
    'en': 'Welcome to SehatSetu Patient Registration. Please fill in the patient name, age, gender, select the village, enter the phone number, and describe the symptoms. Then press the Save Patient Data button.',
    'pa': 'ਸੇਹਤਸੇਤੂ ਮਰੀਜ਼ ਰਜਿਸਟ੍ਰੇਸ਼ਨ ਵਿੱਚ ਤੁਹਾਡਾ ਸਵਾਗਤ ਹੈ। ਕਿਰਪਾ ਕਰਕੇ ਮਰੀਜ਼ ਦਾ ਨਾਮ, ਉਮਰ, ਲਿੰਗ, ਪਿੰਡ ਚੁਣੋ, ਫ਼ੋਨ ਨੰਬਰ ਦਰਜ ਕਰੋ, ਅਤੇ ਲੱਛਣ ਲਿਖੋ। ਫਿਰ ਮਰੀਜ਼ ਡਾਟਾ ਸੇਵ ਕਰੋ ਬਟਨ ਦਬਾਓ।'
}

# Language code mapping for espeak-ng
LANG_MAP = {
    'en': 'en',    # English
    'pa': 'pa'     # Punjabi
}


@tts_bp.route('/api/tts', methods=['GET'])
def text_to_speech():
    """
    Generate speech audio from text using espeak-ng.
    
    Query params:
    - lang: 'en' or 'pa' (default: 'en')
    - text: custom text to speak (optional, uses predefined instructions if not provided)
    
    Returns: WAV audio file
    """
    lang = request.args.get('lang', 'en')
    custom_text = request.args.get('text', None)
    
    # Validate language
    if lang not in LANG_MAP:
        return jsonify({'error': f'Unsupported language: {lang}'}), 400
    
    # Get text to speak
    text = custom_text if custom_text else INSTRUCTIONS.get(lang, INSTRUCTIONS['en'])
    
    # Check if espeak-ng is installed
    if not os.path.exists(ESPEAK_PATH):
        return jsonify({
            'error': 'espeak-ng not installed',
            'install': 'Run: winget install eSpeak-NG.eSpeak-NG'
        }), 500
    
    try:
        # Create temporary WAV file for output
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp_path = tmp.name
        
        # Create temporary text file for input (UTF-8 encoded)
        # This is necessary because Windows command line has issues with Unicode
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as txt_tmp:
            txt_tmp.write(text)
            txt_path = txt_tmp.name
        
        # espeak-ng command:
        # -v <voice>: Voice/language to use
        # -f <file>: Read text from file (handles UTF-8 properly)
        # -w <file>: Write output to WAV file
        # -s <speed>: Speed in words per minute (default 175)
        # -p <pitch>: Pitch adjustment (default 50)
        cmd = [
            ESPEAK_PATH,
            '-v', LANG_MAP[lang],
            '-f', txt_path,
            '-w', tmp_path,
            '-s', '130',    # Slower for clarity
            '-p', '50',     # Default pitch
        ]
        
        # Run espeak-ng
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # Clean up text input file immediately
        try:
            os.unlink(txt_path)
        except:
            pass
        
        if result.returncode != 0:
            return jsonify({
                'error': 'TTS generation failed',
                'details': result.stderr
            }), 500
        
        # Send the audio file
        response = send_file(
            tmp_path,
            mimetype='audio/wav',
            as_attachment=False,
            download_name=f'tts_{lang}.wav'
        )
        
        # Clean up WAV file after sending
        @response.call_on_close
        def cleanup():
            try:
                os.unlink(tmp_path)
            except:
                pass
        
        return response
        
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'TTS generation timed out'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tts_bp.route('/api/tts/voices', methods=['GET'])
def list_voices():
    """
    List available espeak-ng voices.
    Useful for debugging.
    """
    if not os.path.exists(ESPEAK_PATH):
        return jsonify({'error': 'espeak-ng not installed'}), 500
    
    try:
        result = subprocess.run(
            [ESPEAK_PATH, '--voices'],
            capture_output=True,
            text=True,
            timeout=10
        )
        voices = result.stdout.strip().split('\n')
        return jsonify({'voices': voices})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
