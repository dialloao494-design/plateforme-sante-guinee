"""Pydantic schemas for server-side patient dossier (MVP)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

NOTE_TYPES = frozenset({"consultation", "suivi", "urgence"})


class ClinicalNoteCreate(BaseModel):
    note_type: Literal["consultation", "suivi", "urgence"] = "consultation"
    contenu: str = Field(..., min_length=1, max_length=10000)
    appointment_id: Optional[int] = None

    @field_validator("contenu")
    @classmethod
    def strip_contenu(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("contenu cannot be empty")
        return stripped


class ClinicalNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    doctor_id: Optional[int] = None
    appointment_id: Optional[int] = None
    note_type: str
    contenu: str
    created_at: datetime
    updated_at: datetime


class ConsultationSummaryCreate(BaseModel):
    appointment_id: Optional[int] = None
    diagnostic: Optional[str] = Field(None, max_length=10000)
    traitement: Optional[str] = Field(None, max_length=10000)
    recommandations: Optional[str] = Field(None, max_length=10000)

    @field_validator("diagnostic", "traitement", "recommandations")
    @classmethod
    def strip_optional_text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        stripped = v.strip()
        return stripped or None

    def has_content(self) -> bool:
        return bool(self.diagnostic or self.traitement or self.recommandations)


class ConsultationSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    doctor_id: Optional[int] = None
    appointment_id: Optional[int] = None
    diagnostic: Optional[str] = None
    traitement: Optional[str] = None
    recommandations: Optional[str] = None
    created_at: datetime


class PatientDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    uploaded_by: int
    type_document: str
    original_filename: Optional[str] = None
    mime_type: Optional[str] = None
    created_at: datetime
    download_url: Optional[str] = None
    # file_path / storage keys are intentionally omitted (PHI storage hygiene).


class TimelineEvent(BaseModel):
    event_type: str
    resource_id: int
    timestamp: datetime
    summary: str
    payload: dict


class ClinicalAuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: int
    actor_role: str
    patient_id: int
    action: str
    resource_type: str
    resource_id: Optional[int] = None
    timestamp: datetime
    ip: Optional[str] = None
