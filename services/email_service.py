"""Transactional email delivery — SMTP (Railway) or Resend API."""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Iterable

import httpx

logger = logging.getLogger(__name__)


def _env(*keys: str) -> str:
    for key in keys:
        val = (os.getenv(key) or "").strip()
        if val:
            return val
    return ""


def email_config_status() -> dict:
    """Non-secret email channel status for health checks."""
    smtp_host = _env("SMTP_HOST", "SMTP_SERVER")
    resend = _env("RESEND_API_KEY")
    sender = _env("SENDER_EMAIL", "SMTP_FROM", "SMTP_USERNAME", "SMTP_USER")
    frontend = _env("FRONTEND_URL", "FRONTEND_PRODUCTION_URL", "PUBLIC_FRONTEND_URL").rstrip("/")
    return {
        "configured": bool(smtp_host or resend),
        "provider": "resend" if resend else ("smtp" if smtp_host else "none"),
        "sender_set": bool(sender),
        "frontend_url_set": bool(frontend),
        # Public app URL used in reset/verify links — not a secret.
        "frontend_url": frontend or None,
    }


def send_email(
    *,
    to: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> bool:
    """
    Send transactional email. Returns True on success, False if not configured or failed.
    Never raises — callers log and continue (password reset still returns generic success).
    """
    to = to.strip().lower()
    if not to:
        return False

    resend_key = _env("RESEND_API_KEY")
    if resend_key:
        return _send_via_resend(
            api_key=resend_key,
            to=to,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )

    smtp_host = _env("SMTP_HOST", "SMTP_SERVER")
    if smtp_host:
        return _send_via_smtp(
            host=smtp_host,
            to=to,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )

    logger.warning("Email not sent to %s — no SMTP_HOST or RESEND_API_KEY configured", to)
    return False


def _sender_address() -> str:
    return _env("SENDER_EMAIL", "SMTP_FROM", "SMTP_USERNAME", "SMTP_USER") or "noreply@sante-gn.test"


def _send_via_smtp(
    *,
    host: str,
    to: str,
    subject: str,
    text_body: str,
    html_body: str | None,
) -> bool:
    port = int(_env("SMTP_PORT") or "587")
    username = _env("SMTP_USERNAME", "SMTP_USER")
    password = _env("SMTP_PASSWORD", "SMTP_PASS")
    use_tls = _env("SMTP_USE_TLS", "SMTP_TLS").lower() not in ("0", "false", "no")
    use_ssl = _env("SMTP_USE_SSL").lower() in ("1", "true", "yes") or port == 465

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = _sender_address()
    msg["To"] = to
    msg.set_content(text_body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    try:
        if use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as server:
                if username and password:
                    server.login(username, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=30) as server:
                server.ehlo()
                if use_tls:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                    server.ehlo()
                if username and password:
                    server.login(username, password)
                server.send_message(msg)
        logger.info("SMTP email sent to %s subject=%s", to, subject[:60])
        return True
    except Exception as exc:
        logger.exception("SMTP send failed to %s: %s", to, exc)
        return False


def _send_via_resend(
    *,
    api_key: str,
    to: str,
    subject: str,
    text_body: str,
    html_body: str | None,
) -> bool:
    payload = {
        "from": _sender_address(),
        "to": [to],
        "subject": subject,
        "text": text_body,
    }
    if html_body:
        payload["html"] = html_body
    try:
        r = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        if r.status_code >= 400:
            logger.error("Resend API error %s: %s", r.status_code, r.text[:300])
            return False
        logger.info("Resend email sent to %s subject=%s", to, subject[:60])
        return True
    except Exception as exc:
        logger.exception("Resend send failed to %s: %s", to, exc)
        return False


def send_password_reset_email(email: str, link: str) -> bool:
    subject = "Réinitialisation de mot de passe — Plateforme Santé Guinée"
    text = (
        "Bonjour,\n\n"
        "Vous avez demandé la réinitialisation de votre mot de passe.\n"
        f"Ouvrez ce lien (valide 2 heures) : {link}\n\n"
        "Si vous n'êtes pas à l'origine de cette demande, ignorez ce message.\n"
    )
    html = (
        f"<p>Bonjour,</p><p>Cliquez pour réinitialiser votre mot de passe "
        f'(lien valide 2 h) : <a href="{link}">{link}</a></p>'
        "<p>Si vous n'êtes pas à l'origine de cette demande, ignorez ce message.</p>"
    )
    return send_email(to=email, subject=subject, text_body=text, html_body=html)


def send_email_verification_email(email: str, link: str) -> bool:
    subject = "Confirmez votre adresse email — Plateforme Santé Guinée"
    text = (
        "Bonjour,\n\n"
        "Merci de vous être inscrit sur la Plateforme Santé Guinée.\n"
        f"Confirmez votre email : {link}\n\n"
        "Ce lien expire dans 48 heures.\n"
    )
    html = (
        f"<p>Bonjour,</p><p>Confirmez votre adresse email : "
        f'<a href="{link}">Vérifier mon email</a></p><p>Ce lien expire dans 48 heures.</p>'
    )
    return send_email(to=email, subject=subject, text_body=text, html_body=html)
