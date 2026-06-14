"""WhatsApp Cloud API integration architecture."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class WhatsAppService:
    """
    WhatsApp Cloud API client.
    Configure: WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_API_VERSION (default v21.0)
    When not configured, operates in dry-run mode (logs only).
    """

    def __init__(self) -> None:
        self.token = (os.getenv("WHATSAPP_ACCESS_TOKEN") or "").strip()
        self.phone_number_id = (os.getenv("WHATSAPP_PHONE_NUMBER_ID") or "").strip()
        self.api_version = (os.getenv("WHATSAPP_API_VERSION") or "v21.0").strip()
        self.verify_token = (os.getenv("WHATSAPP_VERIFY_TOKEN") or "plateforme-sante-guinee").strip()

    @property
    def configured(self) -> bool:
        return bool(self.token and self.phone_number_id)

    def send_text(self, to_phone: str, body: str) -> dict[str, Any]:
        phone = self._normalize_phone(to_phone)
        if not self.configured:
            logger.info("[WhatsApp dry-run] to=%s body=%s", phone, body[:120])
            return {"dry_run": True, "to": phone, "status": "logged"}
        url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"preview_url": False, "body": body},
        }
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        digits = "".join(c for c in phone if c.isdigit())
        if digits.startswith("0"):
            digits = "224" + digits[1:]
        if not digits.startswith("224") and len(digits) == 9:
            digits = "224" + digits
        return digits

    def appointment_reminder_message(
        self, patient_name: str, doctor_name: str, appt_date: str, hours_before: int
    ) -> str:
        return (
            f"Bonjour {patient_name},\n"
            f"Rappel ({hours_before}h) — RDV avec Dr {doctor_name} le {appt_date}.\n"
            "Répondez CONFIRMER, ANNULER ou REPORTER."
        )
