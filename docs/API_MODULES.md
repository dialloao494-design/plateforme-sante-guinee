# API Modules — Plateforme Santé Guinée v2.0

## Clinical workflow endpoints

| Module | Prefix | Key endpoints |
|--------|--------|---------------|
| Hospitalization | `/clinical/hospitalization` | `GET /occupancy`, `POST /admissions`, `POST /admissions/{id}/assign-bed` |
| Unified billing | `/clinical/billing/unified` | `POST /invoices/generate`, `POST /invoices/{id}/pay`, `GET /invoices/{id}/pdf` |
| Discharge | `/clinical/discharge` | `GET /checklist/{visit_id}`, `POST /execute`, `GET /summaries/{id}/pdf` |
| Radiology | `/clinical/radiology` | `POST /consultations/{id}/orders`, `POST /orders/{id}/report`, `POST /results/{id}/validate` |
| Reminders | `/clinical/reminders` | `GET /notifications`, `POST /appointments/{id}/respond`, `GET/POST /whatsapp/webhook` |

## RBAC summary

| Role | Modules |
|------|---------|
| receptionist | Hospitalization, billing, discharge, notifications |
| doctor | Admission, radiology orders, discharge, notifications |
| lab_technician | Radiology queue & reports |
| admin | All modules + room/bed setup |

## WhatsApp Cloud API

Environment variables:

```
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_API_VERSION=v21.0
WHATSAPP_VERIFY_TOKEN=plateforme-sante-guinee
ENABLE_REMINDER_CRON=true
```

Webhook URL: `https://<api-host>/clinical/reminders/whatsapp/webhook`

## PDF documents

- Invoice PDF: `GET /clinical/billing/unified/invoices/{id}/pdf`
- Discharge PDF: `GET /clinical/discharge/summaries/{id}/pdf`

OpenAPI: `/docs` (when `DOCS_ENABLED=true`)
