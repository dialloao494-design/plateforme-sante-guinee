"""
Server-side Stripe revalidation before any payment settlement.

Settlement MUST NOT trust client-supplied payment identifiers alone — always
cross-check status and amounts against the Stripe API (or injected test doubles).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import stripe
from fastapi import HTTPException, status

from services.stripe_service import StripeService


@dataclass(frozen=True)
class VerifiedStripePayment:
    payment_intent_id: str
    session_id: Optional[str]
    amount_cents: int
    amount_refunded_cents: int
    currency: str
    stripe_status: str
    appointment_id: Optional[int]

    @property
    def net_amount_cents(self) -> int:
        return max(0, self.amount_cents - self.amount_refunded_cents)

    @property
    def is_fully_refunded(self) -> bool:
        return self.amount_cents > 0 and self.amount_refunded_cents >= self.amount_cents

    @property
    def is_partially_refunded(self) -> bool:
        return 0 < self.amount_refunded_cents < self.amount_cents


class StripePaymentVerifier:
    """Retrieve and validate Stripe objects prior to settlement or refund handling."""

    @staticmethod
    def verify_payment_intent(
        payment_intent_id: str,
        *,
        expected_appointment_id: Optional[int] = None,
    ) -> VerifiedStripePayment:
        StripeService.validate_stripe_config()
        try:
            pi = stripe.PaymentIntent.retrieve(payment_intent_id)
        except stripe.error.InvalidRequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stripe payment intent not found: {payment_intent_id}",
            ) from exc
        except stripe.error.StripeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stripe verification failed: {exc}",
            ) from exc

        return StripePaymentVerifier._from_payment_intent(
            pi,
            expected_appointment_id=expected_appointment_id,
        )

    @staticmethod
    def verify_checkout_session(
        session_id: str,
        *,
        expected_appointment_id: Optional[int] = None,
        expected_patient_user_id: Optional[int] = None,
        db=None,
    ) -> VerifiedStripePayment:
        StripeService.validate_stripe_config()
        try:
            session = stripe.checkout.Session.retrieve(session_id, expand=["payment_intent"])
        except stripe.error.InvalidRequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Checkout session not found",
            ) from exc
        except stripe.error.StripeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to verify checkout session: {exc}",
            ) from exc

        if session.get("payment_status") != "paid":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment was not successful or was cancelled on Stripe",
            )

        appointment_id_raw = (session.get("metadata") or {}).get("appointment_id")
        if not appointment_id_raw:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing appointment_id in checkout session metadata",
            )

        appointment_id = int(appointment_id_raw)
        if expected_appointment_id is not None and appointment_id != expected_appointment_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Checkout session appointment mismatch",
            )

        if db is not None and expected_patient_user_id is not None:
            import models

            appointment = (
                db.query(models.RendezVous).filter(models.RendezVous.id == appointment_id).first()
            )
            if not appointment:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
            patient = (
                db.query(models.Patient).filter(models.Patient.id == appointment.patient_id).first()
            )
            if not patient or patient.user_id != expected_patient_user_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        pi_obj = session.get("payment_intent")
        if isinstance(pi_obj, dict):
            proof = StripePaymentVerifier._from_payment_intent_dict(
                pi_obj,
                session_id=session_id,
                appointment_id=appointment_id,
            )
        elif isinstance(pi_obj, str) and pi_obj:
            proof = StripePaymentVerifier.verify_payment_intent(
                pi_obj,
                expected_appointment_id=appointment_id,
            )
            return VerifiedStripePayment(
                payment_intent_id=proof.payment_intent_id,
                session_id=session_id,
                amount_cents=proof.amount_cents,
                amount_refunded_cents=proof.amount_refunded_cents,
                currency=proof.currency,
                stripe_status=proof.stripe_status,
                appointment_id=appointment_id,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Stripe payment intent ID after checkout",
            )

        if proof.appointment_id != appointment_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment intent appointment metadata mismatch",
            )
        return proof

    @staticmethod
    def verify_for_settlement(
        *,
        payment_intent_id: Optional[str],
        session_id: Optional[str],
        expected_appointment_id: Optional[int] = None,
    ) -> VerifiedStripePayment:
        if session_id:
            proof = StripePaymentVerifier.verify_checkout_session(
                session_id,
                expected_appointment_id=expected_appointment_id,
            )
            if payment_intent_id and proof.payment_intent_id != payment_intent_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Payment intent does not match checkout session",
                )
            return proof
        if payment_intent_id:
            return StripePaymentVerifier.verify_payment_intent(
                payment_intent_id,
                expected_appointment_id=expected_appointment_id,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe settlement requires payment_intent_id or session_id",
        )

    @staticmethod
    def assert_settleable(proof: VerifiedStripePayment) -> None:
        if proof.stripe_status != "succeeded":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stripe payment not succeeded (status={proof.stripe_status})",
            )
        if proof.is_fully_refunded:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stripe payment is fully refunded; cannot settle",
            )
        if proof.net_amount_cents <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stripe payment has no receivable amount",
            )

    @staticmethod
    def _from_payment_intent(pi: Any, *, expected_appointment_id: Optional[int]) -> VerifiedStripePayment:
        data = pi.to_dict() if hasattr(pi, "to_dict") else dict(pi)
        return StripePaymentVerifier._from_payment_intent_dict(
            data,
            session_id=None,
            expected_appointment_id=expected_appointment_id,
        )

    @staticmethod
    def _from_payment_intent_dict(
        data: dict,
        *,
        session_id: Optional[str],
        appointment_id: Optional[int] = None,
        expected_appointment_id: Optional[int] = None,
    ) -> VerifiedStripePayment:
        meta = data.get("metadata") or {}
        appt_raw = meta.get("appointment_id")
        resolved_appointment_id = appointment_id
        if appt_raw is not None:
            resolved_appointment_id = int(appt_raw)
        if expected_appointment_id is not None and resolved_appointment_id is not None:
            if resolved_appointment_id != expected_appointment_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Stripe metadata appointment_id mismatch",
                )

        amount = int(data.get("amount_received") or data.get("amount") or 0)
        amount_refunded = int(data.get("amount_refunded") or 0)

        return VerifiedStripePayment(
            payment_intent_id=str(data.get("id") or ""),
            session_id=session_id,
            amount_cents=amount,
            amount_refunded_cents=amount_refunded,
            currency=str(data.get("currency") or "eur").lower(),
            stripe_status=str(data.get("status") or ""),
            appointment_id=resolved_appointment_id,
        )
