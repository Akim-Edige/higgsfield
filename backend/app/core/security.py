"""Security utilities (stubs for demo - no real auth)."""
from uuid import UUID


def get_current_user_id() -> UUID:
    """
    Stub: Return a demo user ID.
    In production, this would validate JWT tokens, etc.
    """
    # For demo purposes, always return the same UUID
    return UUID("00000000-0000-0000-0000-000000000001")

