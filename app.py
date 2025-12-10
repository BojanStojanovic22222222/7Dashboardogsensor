import os
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import re 

# Regex tiføjet til validering af nummmer input
number_pattern = re.compile(r"^\d+(\.\d+)?$")


app = Flask(__name__)

# valg af database baseret på postgresql
if os.getenv("TESTING") == "1":
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://iot_user:iot_password@db:5432/iot_db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Database model for measurements værdier som vi bruger
class Measurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, nullable=False)
    bpm = db.Column(db.Integer, nullable=False)
    spo2 = db.Column(db.Integer, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

 
    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "bpm": self.bpm,
            "spo2": self.spo2,
            "temperature": self.temperature,
            "timestamp": self.timestamp.isoformat()
        }
    
def evaluate_status(m):
    status = "Normal"
    issues = []

    # SpO2 vurdering
    if m.spo2 < 92:
        status = "Kritisk"
        issues.append("Meget lav iltmætning")
    elif m.spo2 < 95:
        status = "Advarsel"
        issues.append("Lav SpO₂")

    # Puls vurdering
    if m.bpm < 50 or m.bpm > 120:
        status = "Kritisk"
        issues.append("Unormal puls")

    # Temperatur vurdering
    if m.temperature > 38.0:
        if status != "Kritisk":
            status = "Advarsel"
        issues.append("Feber")

    return status, issues

#vores main route "/" til dashboardet 
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/data", methods=["POST"])
def receive_data():
    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON"}), 400

    # regex validering og udfylding af tjekliste
    if not number_pattern.match(str(data.get("bpm", ""))):
        return jsonify({"error": "Invalid BPM format"}), 400

    if not number_pattern.match(str(data.get("spo2", ""))):
        return jsonify({"error": "Invalid SpO2 format"}), 400

    if not number_pattern.match(str(data.get("temperature", ""))):
        return jsonify({"error": "Invalid temperature format"}), 400

    m = Measurement(
        patient_id=data.get("patient_id", 1),
        bpm=int(data["bpm"]),
        spo2=int(data["spo2"]),
        temperature=float(data["temperature"]),
        timestamp=datetime.utcfromtimestamp(
            data.get("timestamp", datetime.utcnow().timestamp())
        )
    )

    db.session.add(m)
    db.session.commit()

    return jsonify({"status": "OK"}), 200


@app.route("/api/history")
def history():
    limit = int(request.args.get("limit", 100))
    minutes = request.args.get("minutes")

    query = Measurement.query.order_by(Measurement.timestamp.desc())

    if minutes:
        since = datetime.utcnow() - timedelta(minutes=int(minutes))
        query = query.filter(Measurement.timestamp >= since)

    measurements = query.limit(limit).all()
    measurements = list(reversed(measurements))
    return jsonify([m.to_dict() for m in measurements])

#Tilføjse af Data fra api 

@app.route("/api/stats")
def stats():
    """Returnerer gennemsnit, trends og seneste måling"""
    last = Measurement.query.order_by(Measurement.timestamp.desc()).first()

    if not last:
        return jsonify({"error": "no data"}), 404

    last_10_min = Measurement.query.filter(
        Measurement.timestamp >= datetime.utcnow() - timedelta(minutes=10)
    ).all()

    if last_10_min:
        avg_bpm = sum(m.bpm for m in last_10_min) / len(last_10_min)
        avg_spo2 = sum(m.spo2 for m in last_10_min) / len(last_10_min)
        avg_temp = sum(m.temperature for m in last_10_min) / len(last_10_min)
    else:
        avg_bpm = avg_spo2 = avg_temp = None

    status, issues = evaluate_status(last)

    return jsonify({
        "last_measurement": last.to_dict(),
        "avg_bpm_10min": avg_bpm,
        "avg_spo2_10min": avg_spo2,
        "avg_temp_10min": avg_temp,
        "status": status,
        "issues": issues
    })

# Afslutning på app.py

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000)