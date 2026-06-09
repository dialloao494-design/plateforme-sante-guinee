"""
ORM-level enforcement: privileged roles cannot be written without an authorized channel.
"""

from __future__ import annotations

from sqlalchemy import event, inspect as sa_inspect

from core.provisioning_context import AUTHORIZED_PRIVILEGED_CHANNELS, get_provisioning_channel
from core.roles import PrivilegedRoleAssignmentError, is_privileged_role
from models.user import User


def _assert_privileged_role_persistence(role: str | None) -> None:
    if not role or not is_privileged_role(role):
        return
    channel = get_provisioning_channel()
    if channel not in AUTHORIZED_PRIVILEGED_CHANNELS:
        raise PrivilegedRoleAssignmentError(
            "Privileged role assignment blocked at persistence layer. "
            "Use services.user_provisioning (public register, admin API, or ops bootstrap)."
        )


@event.listens_for(User, "before_insert")
def _user_before_insert(_mapper, _connection, target: User) -> None:
    _assert_privileged_role_persistence(target.role)


@event.listens_for(User, "before_update")
def _user_before_update(_mapper, _connection, target: User) -> None:
    state = sa_inspect(target)
    role_attr = state.attrs.role
    if role_attr.history.has_changes():
        _assert_privileged_role_persistence(target.role)
