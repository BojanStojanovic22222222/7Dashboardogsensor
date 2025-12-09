import os
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

app = flask(__name__)

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