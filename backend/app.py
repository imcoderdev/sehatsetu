import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from routes.triage import triage_bp
from routes.patients import patients_bp
from routes.consultations import consultations_bp
from routes.pharmacy import pharmacy_bp
from routes.sms_webhook import sms_bp
from routes.tts import tts_bp

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
CORS(app)

# Register blueprints
app.register_blueprint(triage_bp)
app.register_blueprint(patients_bp)
app.register_blueprint(consultations_bp)
app.register_blueprint(pharmacy_bp)
app.register_blueprint(sms_bp)
app.register_blueprint(tts_bp)


@app.route('/api/health', methods=['GET'])
def health():
    return {"status": "ok", "service": "SehatSetu API"}


@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    file_path = os.path.join(FRONTEND_DIR, path)
    if os.path.isfile(file_path):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, 'index.html')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
