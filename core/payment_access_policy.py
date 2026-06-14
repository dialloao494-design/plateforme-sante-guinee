"""
Unified payment access policy — single source of truth for treasury gates.

Every business capability that requires a settled payment (teleconsultation join,
appointment confirmation, service delivery) MUST consult this module.

Settlement channels remain in ``core.payment_policy`` / ``payment_settlement``.
"""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, status

import models

# Treasury ledger values that grant service access.
TREASURY_CLEARED_STATUS = "paid"

# Payment states that explicitly revoke prior access (refunds).
ACCESS_REVOKED_PAYMENT_STATUSES = frozenset({"refunded", "partially_refunded"})

# Appointment workflow statuses that may host a paid clinical session.
# ``pending`` and legacy ``paid`` are intentionally excluded — no service without treasury.
BUSINESS_ACTIVE_APPOINTMENT_STATUSES = frozenset(
    {"confirmed", "completed", "checked_in", "active"}
)

# Patient portal: appointment workflow no longer gated by online payment (clinic cashier).
MANUAL_STATUS_TARGETS_REQUIRING_PAYMENT = frozenset()


class PaymentAccessPolicy:
    """Central enforcement for payment-gated business access."""

    @staticmethod
    def normalize_payment_status(value: Optional[str]) -> str:
        return (value or "unpaid").strip().lower()

    @staticmethod
    def normalize_appointment_status(value: Optional[str]) -> str:
        raw = (value or "pending").strip().lower()
        if raw in {"confirmé", "confirmee"}:
            return "confirmed"
        return raw

    @staticmethod
    def is_treasury_cleared(appointment: models.RendezVous) -> bool:
        return (
            PaymentAccessPolicy.normalize_payment_status(appointment.payment_status)
            == TREASURY_CLEARED_STATUS
        )

    @staticmethod
    def is_access_revoked(appointment: models.RendezVous) -> bool:
        return (
            PaymentAccessPolicy.normalize_payment_status(appointment.payment_status)
            in ACCESS_REVOKED_PAYMENT_STATUSES
        )

    @staticmethod
    def is_business_active_status(appointment: models.RendezVous) -> bool:
        return (
            PaymentAccessPolicy.normalize_appointment_status(appointment.status)
            in BUSINESS_ACTIVE_APPOINTMENT_STATUSES
        )

    @staticmethod
    def assert_treasury_cleared(
        appointment: models.RendezVous,
        *,
        context: str = "service access",
    ) -> None:
        if PaymentAccessPolicy.is_access_revoked(appointment):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Accès révoqué : le paiement a été remboursé. "
                    f"({context})"
                ),
            )
        if not PaymentAccessPolicy.is_treasury_cleared(appointment):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Paiement requis avant d'accéder à ce service. "
                    f"({context})"
                ),
            )

    @staticmethod
    def assert_status_transition_allowed(
        appointment: models.RendezVous,
        new_status: str,
    ) -> None:
        """Allow workflow transitions without online treasury (payment at clinic cashier)."""
        target = PaymentAccessPolicy.normalize_appointment_status(new_status)
        if target == "confirmed" and PaymentAccessPolicy.is_access_revoked(appointment):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Impossible de confirmer : le paiement a été remboursé.",
            )

    @staticmethod
    def evaluate_teleconsult_gate(
        appointment: models.RendezVous,
    ) -> Optional[dict[str, object]]:
        """
        Non-throwing teleconsult eligibility pre-check (payment + workflow status).

        Returns a block payload or None when payment gate passes (time window checked separately).
        """
        if PaymentAccessPolicy.is_access_revoked(appointment):
            ps = PaymentAccessPolicy.normalize_payment_status(appointment.payment_status)
            return {
                "can_join": False,
                "reason": "payment_revoked",
                "message": (
                    "Accès révoqué : remboursement enregistré. "
                    "La téléconsultation n'est plus disponible."
                    if ps == "refunded"
                    else "Accès suspendu : remboursement partiel en cours."
                ),
                "payment_status": appointment.payment_status,
            }

        status_norm = PaymentAccessPolicy.normalize_appointment_status(appointment.status)
        if status_norm in {"cancelled", "expired"}:
            return None  # handled upstream

        if status_norm not in BUSINESS_ACTIVE_APPOINTMENT_STATUSES:
            return {
                "can_join": False,
                "reason": "status_blocked",
                "message": (
                    "Le rendez-vous doit être confirmé avant d'ouvrir la salle. "
                    f"(statut actuel : {appointment.status})"
                ),
                "status": appointment.status,
            }

        return None

    @staticmethod
    def assert_teleconsult_access(appointment: models.RendezVous) -> None:
        """Throwing guard used before issuing Jitsi credentials."""
        block = PaymentAccessPolicy.evaluate_teleconsult_gate(appointment)
        if block:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(block.get("message") or "Accès téléconsultation refusé."),
            )
