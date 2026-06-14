"""
Appointment — clinical scheduling entity.

Persisted in the legacy `rendezvous` table until a dedicated rename migration.
"""

from models.rendezvous import RendezVous

Appointment = RendezVous

__all__ = ["Appointment", "RendezVous"]
