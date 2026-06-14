import sqlite3
from pathlib import Path

db = Path(__file__).resolve().parents[1] / "sante.db"
c = sqlite3.connect(db)
queries = [
    ("patients", "SELECT COUNT(*) FROM patients"),
    ("sim_patients", "SELECT COUNT(*) FROM patients WHERE last_name LIKE 'sim_history_%'"),
    ("appointments", "SELECT COUNT(*) FROM rendezvous"),
    ("consultations", "SELECT COUNT(*) FROM consultations"),
    ("lab_orders", "SELECT COUNT(*) FROM lab_orders"),
    ("prescriptions", "SELECT COUNT(*) FROM prescriptions"),
    ("follow_ups", "SELECT COUNT(*) FROM follow_up_schedules"),
    ("medical_records", "SELECT COUNT(*) FROM patient_medical_records"),
    ("audit_logs", "SELECT COUNT(*) FROM clinical_audit_logs"),
]
for name, sql in queries:
    try:
        print(f"{name}={c.execute(sql).fetchone()[0]}")
    except Exception as e:
        print(f"{name}=ERR:{e}")
