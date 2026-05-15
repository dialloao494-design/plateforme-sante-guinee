"""API rate limiting (slowapi)."""

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

_default = os.getenv("RATE_LIMIT_DEFAULT", "200/minute")

limiter = Limiter(key_func=get_remote_address, default_limits=[_default])
