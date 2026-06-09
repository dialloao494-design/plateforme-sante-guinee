-- Patient dossier MVP (A1) — PostgreSQL / SQLite compatible reference migration
-- Applied automatically via Alembic (20260525_0003_patient_dossier) and database_migrations.ensure_patient_dossier_schema

-- Extend patients table
ALTER TABLE patients ADD COLUMN IF NOT EXISTS date_of_birth DATE;
ALTER TABLE patients ADD COLUMN IF NOT EXISTS phone VARCHAR(32);
ALTER TABLE patients ADD COLUMN IF NOT EXISTS address TEXT;
ALTER TABLE patients ADD COLUMN IF NOT EXISTS emergency_contact VARCHAR(255);
ALTER TABLE patients ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL;
ALTER TABLE patients ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL;

CREATE TABLE IF NOT EXISTS clinical_notes (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    doctor_id INTEGER REFERENCES doctors(id),
    appointment_id INTEGER REFERENCES rendezvous(id),
    note_type VARCHAR(32) NOT NULL DEFAULT 'consultation',
    contenu TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS consultation_summaries (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    doctor_id INTEGER REFERENCES doctors(id),
    appointment_id INTEGER REFERENCES rendezvous(id),
    diagnostic TEXT,
    traitement TEXT,
    recommandations TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS patient_documents (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    uploaded_by INTEGER NOT NULL REFERENCES users(id),
    type_document VARCHAR(64) NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS clinical_audit_logs (
    id SERIAL PRIMARY KEY,
    actor_id INTEGER NOT NULL REFERENCES users(id),
    actor_role VARCHAR(32) NOT NULL,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    action VARCHAR(32) NOT NULL,
    resource_type VARCHAR(64) NOT NULL,
    resource_id INTEGER,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ip VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS ix_clinical_notes_patient_id ON clinical_notes(patient_id);
CREATE INDEX IF NOT EXISTS ix_consultation_summaries_patient_id ON consultation_summaries(patient_id);
CREATE INDEX IF NOT EXISTS ix_patient_documents_patient_id ON patient_documents(patient_id);
CREATE INDEX IF NOT EXISTS ix_clinical_audit_logs_patient_id ON clinical_audit_logs(patient_id);
CREATE INDEX IF NOT EXISTS ix_clinical_audit_logs_timestamp ON clinical_audit_logs(timestamp);
