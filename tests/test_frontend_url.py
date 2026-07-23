"""Canonical frontend URL remaps legacy Vercel host."""

from __future__ import annotations

import os

from core.frontend_url import (
    CANONICAL_FRONTEND_URL,
    frontend_url_status,
    resolve_frontend_url,
)


def test_remaps_legacy_seven_rust(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "https://frontend-seven-rust-94.vercel.app")
    monkeypatch.delenv("FRONTEND_PRODUCTION_URL", raising=False)
    monkeypatch.delenv("PUBLIC_FRONTEND_URL", raising=False)
    assert resolve_frontend_url() == CANONICAL_FRONTEND_URL
    status = frontend_url_status()
    assert status["frontend_url"] == CANONICAL_FRONTEND_URL
    assert status["frontend_url_remapped_from_legacy"] is True
    assert status["frontend_url_raw"] == "https://frontend-seven-rust-94.vercel.app"


def test_keeps_canonical(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", CANONICAL_FRONTEND_URL)
    assert resolve_frontend_url() == CANONICAL_FRONTEND_URL
    assert frontend_url_status()["frontend_url_remapped_from_legacy"] is False


def test_reset_and_verify_links_use_canonical(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "https://frontend-seven-rust-94.vercel.app/")
    from services.password_reset_service import build_reset_link
    from services.email_verification_service import build_verify_link

    assert build_reset_link("tok123").startswith(f"{CANONICAL_FRONTEND_URL}/reset-password?")
    assert build_verify_link("tok456").startswith(f"{CANONICAL_FRONTEND_URL}/verify-email?")
