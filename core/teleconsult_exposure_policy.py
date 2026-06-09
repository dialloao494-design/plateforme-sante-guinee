"""
Teleconsultation URL exposure policy — payment-gated, API-safe.

Jitsi join credentials MUST NOT be reachable before treasury settlement.
Public appointment APIs never publish join URLs; credentials are issued only
via authenticated ``/teleconsultation/.../access`` after PaymentAccessPolicy passes.
"""

from __future__ import annotations

from typing import Optional

import models
from core.payment_access_policy import PaymentAccessPolicy


class TeleconsultExposurePolicy:
    """Controls when meeting URLs may leave the server."""

    @staticmethod
    def is_teleconsultation(appointment: models.RendezVous) -> bool:
        return (appointment.consultation_type or "").lower().strip() == "teleconsultation"

    @staticmethod
    def may_issue_join_credentials(appointment: models.RendezVous) -> bool:
        """True when /teleconsultation/access may embed meeting_url + JWT."""
        if not TeleconsultExposurePolicy.is_teleconsultation(appointment):
            return False
        if PaymentAccessPolicy.is_access_revoked(appointment):
            return False
        if not PaymentAccessPolicy.is_treasury_cleared(appointment):
            return False
        if not PaymentAccessPolicy.is_business_active_status(appointment):
            return False
        return True

    @staticmethod
    def api_meeting_link(appointment: models.RendezVous | object) -> None:
        """
        Appointment list/detail APIs never expose join URLs (defense in depth).

        Even after payment, clients must call /teleconsultation/.../access.
        """
        return None

    @staticmethod
    def sanitize_stored_meeting_link(
        appointment: models.RendezVous,
        *,
        link: Optional[str],
    ) -> Optional[str]:
        """Persist meeting_link only after treasury clearance (internal cache optional)."""
        if not link:
            return None
        if not TeleconsultExposurePolicy.may_issue_join_credentials(appointment):
            return None
        return link
