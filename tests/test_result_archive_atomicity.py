"""Validation, archived result and audit must succeed or fail together."""
from datetime import datetime
import uuid

from fastapi import HTTPException
import pytest

import models
from services.clinical_workflow_service import ClinicalWorkflowService
from services.imaging_service import ImagingService
from services.clinical_audit_service import ClinicalAuditService
from tests.test_redteam_round2_clinical_idor import _clinic, _doctor, _patient


@pytest.fixture
def result_context(db_session, tmp_path, monkeypatch):
    monkeypatch.setenv("SECURE_ATTACHMENT_ROOT", str(tmp_path))
    monkeypatch.setenv("ATTACHMENT_VIRUS_SCAN", "off")
    suffix = uuid.uuid4().hex
    clinic = _clinic(db_session, f"Archive {suffix}")
    doctor = _doctor(db_session, clinic_id=clinic.id, email=f"archive-{suffix}@example.test")
    patient = _patient(db_session, clinic_id=clinic.id)
    appointment = models.RendezVous(clinic_id=clinic.id, patient_id=patient.id,
        doctor_id=doctor.id, date=datetime.utcnow(), status="confirmed")
    db_session.add(appointment)
    db_session.flush()
    consultation = models.ClinicalConsultation(clinic_id=clinic.id, patient_id=patient.id,
        doctor_id=doctor.id, appointment_id=appointment.id, status="in_progress")
    db_session.add(consultation)
    db_session.flush()
    lab_order = models.LabOrder(clinic_id=clinic.id, consultation_id=consultation.id,
        patient_id=patient.id, doctor_id=doctor.id, ordered_by_user_id=doctor.user_id,
        test_code="synthetic", test_name="Synthetic test", status="in_analysis")
    image_order = models.ImagingOrder(clinic_id=clinic.id, consultation_id=consultation.id,
        patient_id=patient.id, modality="xray", status="reported")
    db_session.add_all([lab_order, image_order])
    db_session.flush()
    lab = models.LabResult(lab_order_id=lab_order.id, recorded_by_user_id=doctor.user_id,
        result_summary="Synthetic finding", status="draft")
    image = models.ImagingResult(order_id=image_order.id, findings="Synthetic finding", status="reported")
    db_session.add_all([lab, image])
    db_session.commit()
    return clinic, doctor.user, patient, lab, image, tmp_path


def _validate(db, context, kind):
    clinic, actor, _, lab, image, _ = context
    if kind == "lab":
        return ClinicalWorkflowService.validate_lab_result(db, clinic_id=clinic.id,
            result_id=lab.id, user=actor)
    return ImagingService.validate_report(db, clinic_id=clinic.id, result_id=image.id, actor=actor)


def _assert_counts(db, context, kind, expected):
    _, _, patient, lab, image, root = context
    doc_type = "lab_result" if kind == "lab" else "imaging_report"
    resource_type = "lab_result_validate" if kind == "lab" else "imaging_result"
    result = lab if kind == "lab" else image
    assert db.query(models.PatientDocument).filter_by(patient_id=patient.id, type_document=doc_type).count() == expected
    assert db.query(models.ClinicalAuditLog).filter_by(patient_id=patient.id,
        resource_type=resource_type, resource_id=result.id).count() == expected
    if kind == "imaging":
        assert db.query(models.ClinicalNote).filter_by(patient_id=patient.id, note_type="imaging").count() == expected
    assert len([p for p in root.rglob("*") if p.is_file()]) == expected


@pytest.mark.parametrize("kind", ["lab", "imaging"])
@pytest.mark.parametrize("failure", ["scanner", "audit"])
def test_result_archive_failure_is_atomic_and_retry_is_idempotent(db_session, result_context, monkeypatch, kind, failure):
    context = result_context
    result = context[3] if kind == "lab" else context[4]
    order = result.lab_order if kind == "lab" else result.order
    original_status, original_order_status = result.status, order.status
    with monkeypatch.context() as patch:
        if failure == "scanner":
            def reject(*args, **kwargs):
                raise HTTPException(status_code=503, detail="Synthetic scanner unavailable")
            patch.setattr("services.secure_attachment_storage.scan_attachment_bytes", reject)
            error = HTTPException
        else:
            original_log = ClinicalAuditService.log
            def reject(*args, **kwargs):
                original_log(*args, **kwargs)
                raise RuntimeError("Synthetic audit unavailable")
            patch.setattr(ClinicalAuditService, "log", reject)
            error = RuntimeError
        with pytest.raises(error):
            _validate(db_session, context, kind)
    # A caller must not be able to accidentally commit partial validation later.
    db_session.commit()
    db_session.expire_all()
    assert result.status == original_status
    assert order.status == original_order_status
    assert result.validated_at is None and result.validated_by_user_id is None
    _assert_counts(db_session, context, kind, 0)

    _validate(db_session, context, kind)
    assert result.status == "validated"
    assert order.status == ("completed" if kind == "lab" else "validated")
    validated_at = result.validated_at
    _assert_counts(db_session, context, kind, 1)
    _validate(db_session, context, kind)
    assert result.validated_at == validated_at
    _assert_counts(db_session, context, kind, 1)


def test_edited_lab_result_requires_fresh_validation_and_archive(db_session, result_context):
    from schemas.clinical import LabResultCreate

    clinic, actor, _, result, _, _ = result_context
    _validate(db_session, result_context, "lab")
    _assert_counts(db_session, result_context, "lab", 1)
    ClinicalWorkflowService.record_lab_result(
        db_session, clinic_id=clinic.id, order_id=result.lab_order_id, user=actor,
        payload=LabResultCreate(result_summary="Revised synthetic finding"),
    )
    assert result.status == "draft"
    assert result.validated_at is None and result.validated_by_user_id is None
    _validate(db_session, result_context, "lab")
    assert result.status == "validated"
    _assert_counts(db_session, result_context, "lab", 2)
    _validate(db_session, result_context, "lab")
    _assert_counts(db_session, result_context, "lab", 2)
