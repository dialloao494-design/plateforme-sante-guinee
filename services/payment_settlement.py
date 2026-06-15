"""
Central payment settlement for appointments (admin manual / dev stub only).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import models
from core.payment_policy import (
    SETTLEMENT_CHANNEL_ADMIN_MANUAL,
    SETTLEMENT_CHANNEL_DEV_STUB,
    assert_settlement_channel,
    is_stub_settlement_allowed,
    validate_stub_token,
)
from models.user import User

logger = logging.getLogger(__name__)


class PaymentSettlementError(Exception):
    """Settlement rejected by policy."""


def _assert_actor_is_admin(db: Session, actor_user_id: int) -> User:
    user = db.query(User).filter(User.id == actor_user_id).first()
    if not user or user.role not in ("platform_admin", "clinic_admin", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required for manual payment settlement",
        )
    return user


def _upsert_payment_record(
    db: Session,
    *,
    appointment_id: int,
    payment_id: str,
    amount: int,
    currency: str,
    status_value: str,
    settlement_channel: str,
) -> None:
    existing = (
        db.query(models.Payment)
        .filter(models.Payment.appointment_id == appointment_id, models.Payment.status == "paid")
        .first()
    )
    if existing:
        return
    record = models.Payment(
        appointment_id=appointment_id,
        payment_id=payment_id,
        amount=amount,
        currency=currency,
        status=status_value,
        settlement_channel=settlement_channel,
    )
    db.add(record)


class PaymentSettlementService:
    @staticmethod
    def settle_appointment(
        db: Session,
        appointment_id: int,
        *,
        channel: str,
        actor_user_id: Optional[int] = None,
        stub_token: Optional[str] = None,
        amount_cents: Optional[int] = None,
        currency: str = "gnf",
        admin_reference: Optional[str] = None,
    ) -> models.RendezVous:
        from services.rendezvous_service import RendezVousService

        normalized_channel = assert_settlement_channel(channel)
        RendezVousService.ensure_schema(db)

        appointment = (
            db.query(models.RendezVous)
            .filter(models.RendezVous.id == appointment_id)
            .with_for_update()
            .first()
        )
        if not appointment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

        if appointment.status == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot settle payment for cancelled appointment",
            )

        if appointment.payment_status in {"refunded", "partially_refunded"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot settle: appointment payment_status is '{appointment.payment_status}'",
            )

        if appointment.status == "confirmed" and appointment.payment_status == "paid":
            logger.info(
                "Settlement skipped (already settled) appointment_id=%s channel=%s",
                appointment_id,
                normalized_channel,
            )
            return appointment

        if normalized_channel == SETTLEMENT_CHANNEL_ADMIN_MANUAL:
            if actor_user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Manual settlement requires an authenticated administrator",
                )
            _assert_actor_is_admin(db, actor_user_id)

        PaymentSettlementService._authorize_channel(normalized_channel, stub_token=stub_token)

        if appointment.status not in {"pending", "paid"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot settle payment for appointment with status '{appointment.status}'",
            )

        if normalized_channel == SETTLEMENT_CHANNEL_DEV_STUB:
            payment_id = f"stub-{appointment_id}-{uuid.uuid4().hex[:12]}"
        else:
            ref = (admin_reference or "manual").strip()[:40]
            payment_id = f"manual-{actor_user_id}-{appointment_id}-{ref}"

        verified_amount = amount_cents if amount_cents is not None else int((appointment.price or 0) * 100)
        verified_currency = (currency or "gnf").lower()

        appointment.status = "confirmed"
        appointment.payment_status = "paid"
        appointment.payment_intent_id = payment_id
        appointment.updated_at = datetime.utcnow()

        _upsert_payment_record(
            db,
            appointment_id=appointment.id,
            payment_id=payment_id,
            amount=verified_amount,
            currency=verified_currency,
            status_value="paid",
            settlement_channel=normalized_channel,
        )

        db.commit()
        db.refresh(appointment)

        logger.info(
            "Appointment settled appointment_id=%s channel=%s actor_user_id=%s payment_id=%s",
            appointment.id,
            normalized_channel,
            actor_user_id,
            payment_id,
        )
        return appointment

    @staticmethod
    def assert_checkout_allowed(db: Session, appointment_id: int) -> models.RendezVous:
        appointment = (
            db.query(models.RendezVous)
            .filter(models.RendezVous.id == appointment_id)
            .with_for_update()
            .first()
        )
        if not appointment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

        if appointment.payment_status == "paid" and appointment.status == "confirmed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Appointment is already paid and confirmed",
            )

        paid_record = (
            db.query(models.Payment)
            .filter(models.Payment.appointment_id == appointment_id, models.Payment.status == "paid")
            .first()
        )
        if paid_record:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A successful payment already exists for this appointment",
            )

        db.commit()
        return appointment

    @staticmethod
    def _authorize_channel(channel: str, *, stub_token: Optional[str]) -> None:
        if channel == SETTLEMENT_CHANNEL_ADMIN_MANUAL:
            return

        if channel == SETTLEMENT_CHANNEL_DEV_STUB:
            if not is_stub_settlement_allowed():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Stub payment settlement is disabled.",
                )
            if not validate_stub_token(stub_token):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid or missing payment stub token",
                )
            return

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unhandled settlement channel authorization: {channel}",
        )
