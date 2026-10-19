"""``geo.union_etl`` — every ``*_etl`` table stacked into one (written by GEO_ETL).

The union table carries the canonical 21 columns of GEO_ETL's
``model/etl/event_etl.py``; ``source_name`` says which of the nine source
tables a row came from. It is declared here as a SQLAlchemy **Core table**
instead of an SQLModel entity on purpose: the stacked table has no primary
key — rows are deduplicated per source and ``file_date``, so nothing in the
21 columns is unique — and the ORM mapper refuses a table without one. The
API only reads the table (GEO_ETL owns it), so the table object is all the
provider needs to build ``SELECT`` / ``GROUP BY`` statements.
"""

from sqlalchemy import MetaData, Table
from sqlmodel import Column, DateTime, Float, String

union_etl = Table(
    "union_etl",
    MetaData(),
    Column("source_name", String, nullable=False),
    Column("subsource_name", String),
    Column("event_name", String),
    Column("event_category", String, nullable=False),
    Column("event_subcategory", String),
    Column("event_description", String),
    Column("latitude", Float),
    Column("longitude", Float),
    Column("country_code", String, nullable=False),
    Column("state_province", String),
    Column("place_location", String),
    Column("metric_name", String, nullable=False),
    Column("metric_value", Float),
    Column("metric_unit", String),
    Column("danger_rating", String),
    Column("other_metrics", String),
    Column("event_start", DateTime),
    Column("event_end", DateTime),
    Column("last_latitude", Float),
    Column("last_longitude", Float),
    Column("file_date", String, nullable=False),
    schema="geo",
)
