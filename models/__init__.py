from .patient import Patient
from .rendezvous import RendezVous
from .payment import Payment
from .user import User
from .doctor import Doctor
from .availability import DoctorAvailability
from .message import Message
from .attachment_access_log import AttachmentAccessLog
from .notification_event import NotificationEvent
from .stripe_webhook_event import StripeWebhookEvent
from .clinical_note import ClinicalNote
from .consultation_summary import ConsultationSummary
from .patient_document import PatientDocument
from .clinical_audit_log import ClinicalAuditLog

# Register ORM hooks (privileged role guard) after User is defined.
from . import user_hooks as _user_hooks  # noqa: F401
