"""
Authorized provisioning channels for privileged (admin) account persistence.

SQLAlchemy hooks on ``User`` read this context to block direct ORM inserts/updates
that assign ``admin`` outside approved code paths.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

# Channels allowed to persist role=admin via the ORM layer.
AUTHORIZED_PRIVILEGED_CHANNELS: frozenset[str] = frozenset(
    {
        "admin_api",
        "admin_bootstrap",
        "admin_cli",
        "test_fixture",
        "platform_owner_bootstrap",
        "platform_owner_setup",
    }
)

_provisioning_channel: ContextVar[str | None] = ContextVar(
    "user_provisioning_channel",
    default=None,
)


def get_provisioning_channel() -> str | None:
    return _provisioning_channel.get()


@contextmanager
def provisioning_channel(channel: str) -> Iterator[None]:
    """Mark the current execution context as an authorized user-provisioning channel."""
    token = _provisioning_channel.set(channel)
    try:
        yield
    finally:
        _provisioning_channel.reset(token)
