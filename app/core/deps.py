"""
Backward-compatible dependency exports.

Prefer importing from `app.core.dependencies` in new code.
"""

from app.core.dependencies import (
    DBSession,
    get_current_user,
    get_db,
    oauth2_scheme,
    require_roles,
)

require_admin = require_roles("ADMIN")
require_tl = require_roles("TECHNICAL_LEAD")
require_intern = require_roles("INTERN")
require_admin_or_tl = require_roles("ADMIN", "TECHNICAL_LEAD")

__all__ = [
    "DBSession",
    "get_db",
    "get_current_user",
    "oauth2_scheme",
    "require_roles",
    "require_admin",
    "require_tl",
    "require_intern",
    "require_admin_or_tl",
]
