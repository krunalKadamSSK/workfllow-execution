"""Authentication / authorization stubs (not yet implemented).

Future home for API keys, JWT validation, and permission checks.
Wire dependencies from ``app.core.dependencies`` when auth lands.
"""


class SecurityPlaceholder:
    """Marks the auth boundary until real security middleware exists."""

    def is_authenticated(self) -> bool:
        return False
