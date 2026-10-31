"""Data providers."""

# Database providers
from provider.db.i_db_data_quality_provider import IDbDataQualityProvider
from provider.db.i_db_data_quantity_provider import IDbDataQuantityProvider
from provider.db.i_db_event_counts_provider import IDbEventCountsProvider
from provider.db.i_db_provider import IDbProvider

# Supabase Postgres providers
from provider.supabase_postgres.supabase_postgres_data_quality_provider import SupabasePostgresDbDataQualityProvider
from provider.supabase_postgres.supabase_postgres_data_quantity_provider import (
    SupabasePostgresDbDataQuantityProvider,
)
from provider.supabase_postgres.supabase_postgres_event_counts_provider import (
    SupabasePostgresDbEventCountsProvider,
)
from provider.supabase_postgres.supabase_postgres_provider import (
    SupabasePostgresProvider,
    dispose_provider,
    get_provider,
    get_session,
)

__all__ = [
    "IDbDataQualityProvider",
    "IDbDataQuantityProvider",
    "IDbEventCountsProvider",
    "IDbProvider",
    "SupabasePostgresDbDataQualityProvider",
    "SupabasePostgresDbDataQuantityProvider",
    "SupabasePostgresDbEventCountsProvider",
    "SupabasePostgresProvider",
    "dispose_provider",
    "get_provider",
    "get_session",
]
