"""Custom exceptions for GEO_API."""


class SupabaseServerDownError(Exception):
    """Raised when the Supabase Postgres server is down or unreachable."""
