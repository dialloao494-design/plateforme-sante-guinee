"""

Central payment settlement for appointments.



All transitions to payment_status=paid + status=confirmed MUST pass through this module

with an explicit, auditable settlement channel and supporting evidence.



Production guarantees:

- Row-level lock (SELECT FOR UPDATE) on appointment during transition

- Stripe API revalidation for stripe_* channels before any state change

- Single atomic commit (no intermediate paid→confirmed double commit)

- Idempotent when already settled; rejects conflicting second payment_intent

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

    SETTLEMENT_CHANNEL_STRIPE_CHECKOUT,

    SETTLEMENT_CHANNEL_STRIPE_WEBHOOK,

    assert_settlement_channel,

    is_stub_settlement_allowed,

    validate_stub_token,

)

from models.user import User

from services.stripe_verification import StripePaymentVerifier



logger = logging.getLogger(__name__)





class PaymentSettlementError(Exception):

    """Settlement rejected by policy."""





def _assert_actor_is_admin(db: Session, actor_user_id: int) -> User:

    user = db.query(User).filter(User.id == actor_user_id).first()

    if not user or user.role != "admin":

        raise HTTPException(

            status_code=status.HTTP_403_FORBIDDEN,

            detail="Administrator privileges required for manual payment settlement",

        )

    return user





class PaymentSettlementService:

    @staticmethod

    def settle_appointment(

        db: Session,

        appointment_id: int,

        *,

        channel: str,

        actor_user_id: Optional[int] = None,

        stub_token: Optional[str] = None,

        stripe_payment_intent_id: Optional[str] = None,

        stripe_session_id: Optional[str] = None,

        stripe_event_id: Optional[str] = None,

        amount_cents: Optional[int] = None,

        currency: str = "eur",

        admin_reference: Optional[str] = None,

    ) -> models.RendezVous:

        """

        Mark an appointment paid and confirmed after verified settlement evidence.



        Idempotent when already paid+confirmed with the same payment_intent.

        """

        from services.rendezvous_service import RendezVousService

        from services.stripe_service import StripeService



        normalized_channel = assert_settlement_channel(channel)

        RendezVousService.ensure_schema(db)



        appointment = (

            db.query(models.RendezVous)

            .filter(models.RendezVous.id == appointment_id)

            .with_for_update()

            .first()

        )

        if not appointment:

            raise HTTPException(

                status_code=status.HTTP_404_NOT_FOUND,

                detail="Appointment not found",

            )



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

            if stripe_payment_intent_id and appointment.payment_intent_id:

                if appointment.payment_intent_id != stripe_payment_intent_id:

                    raise HTTPException(

                        status_code=status.HTTP_409_CONFLICT,

                        detail="Appointment already paid with a different Stripe payment intent",

                    )

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



        PaymentSettlementService._authorize_channel(

            normalized_channel,

            stub_token=stub_token,

            stripe_payment_intent_id=stripe_payment_intent_id,

            stripe_session_id=stripe_session_id,

        )



        if appointment.status not in {"pending", "paid"}:

            raise HTTPException(

                status_code=status.HTTP_400_BAD_REQUEST,

                detail=f"Cannot settle payment for appointment with status '{appointment.status}'",

            )



        if appointment.payment_status == "paid" and appointment.payment_intent_id:

            if (

                stripe_payment_intent_id

                and appointment.payment_intent_id != stripe_payment_intent_id

            ):

                raise HTTPException(

                    status_code=status.HTTP_409_CONFLICT,

                    detail="Appointment already paid with a different payment",

                )

            appointment.status = "confirmed"

            appointment.updated_at = datetime.utcnow()

            db.commit()

            db.refresh(appointment)

            return appointment



        verified_amount = amount_cents

        verified_currency = (currency or "eur").lower()



        if normalized_channel in {

            SETTLEMENT_CHANNEL_STRIPE_CHECKOUT,

            SETTLEMENT_CHANNEL_STRIPE_WEBHOOK,

        }:

            proof = StripePaymentVerifier.verify_for_settlement(

                payment_intent_id=stripe_payment_intent_id,

                session_id=stripe_session_id,

                expected_appointment_id=appointment_id,

            )

            StripePaymentVerifier.assert_settleable(proof)

            stripe_payment_intent_id = proof.payment_intent_id

            verified_amount = proof.net_amount_cents

            verified_currency = proof.currency



        payment_id = stripe_payment_intent_id or ""

        if normalized_channel == SETTLEMENT_CHANNEL_DEV_STUB:

            payment_id = f"stub-{appointment_id}-{uuid.uuid4().hex[:12]}"

        elif normalized_channel == SETTLEMENT_CHANNEL_ADMIN_MANUAL:

            ref = (admin_reference or "manual").strip()[:40]

            payment_id = f"manual-{actor_user_id}-{appointment_id}-{ref}"



        if not payment_id and stripe_session_id:

            payment_id = stripe_session_id



        if not payment_id:

            raise HTTPException(

                status_code=status.HTTP_400_BAD_REQUEST,

                detail="Missing payment identifier for settlement audit trail",

            )



        amount = verified_amount if verified_amount is not None else int((appointment.price or 0) * 100)



        appointment.status = "confirmed"

        appointment.payment_status = "paid"

        appointment.payment_intent_id = payment_id

        appointment.updated_at = datetime.utcnow()



        StripeService._upsert_payment_record(

            db=db,

            appointment_id=appointment.id,

            payment_id=payment_id,

            stripe_session_id=stripe_session_id,

            amount=amount,

            currency=verified_currency,

            status_value="paid",

            settlement_channel=normalized_channel,

            stripe_event_id=stripe_event_id,

        )



        db.commit()

        db.refresh(appointment)



        logger.info(

            "Appointment settled appointment_id=%s channel=%s actor_user_id=%s payment_id=%s event=%s",

            appointment.id,

            normalized_channel,

            actor_user_id,

            payment_id,

            stripe_event_id,

        )

        return appointment



    @staticmethod

    def assert_checkout_allowed(db: Session, appointment_id: int) -> models.RendezVous:

        """Guard create-intent against double payment attempts."""

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

            .filter(

                models.Payment.appointment_id == appointment_id,

                models.Payment.status == "paid",

            )

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

    def _authorize_channel(

        channel: str,

        *,

        stub_token: Optional[str],

        stripe_payment_intent_id: Optional[str],

        stripe_session_id: Optional[str],

    ) -> None:

        if channel in {SETTLEMENT_CHANNEL_STRIPE_CHECKOUT, SETTLEMENT_CHANNEL_STRIPE_WEBHOOK}:

            if not stripe_payment_intent_id and not stripe_session_id:

                raise HTTPException(

                    status_code=status.HTTP_400_BAD_REQUEST,

                    detail="Stripe settlement requires payment_intent_id or session_id evidence",

                )

            return



        if channel == SETTLEMENT_CHANNEL_ADMIN_MANUAL:

            return



        if channel == SETTLEMENT_CHANNEL_DEV_STUB:

            if not is_stub_settlement_allowed():

                raise HTTPException(

                    status_code=status.HTTP_403_FORBIDDEN,

                    detail=(

                        "Stub payment settlement is disabled. "

                        "Use Stripe Checkout (/payments/create-intent) and "

                        "/payments/confirm-checkout after payment."

                    ),

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


