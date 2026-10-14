"""Data quality metrics — row layout of ``geo.data_quality`` (written by GEO_ETL)."""

import datetime as dt

from pydantic import ConfigDict
from sqlmodel import Column, DateTime, Field, Float, SQLModel, String


class DataQuality(SQLModel, table=True):
    """One data quality metric value for one ``file_date`` of one table.

    Stored long-format (one row per metric) by GEO_ETL's DATA_QUALITY job, so
    history, trends and threshold queries are plain SQL against
    ``geo.data_quality``. ``file_date`` is either a ``YYYY-MM-DD`` snapshot
    date or the special value ``"overall"`` (whole-table snapshot).

    Attributes:
        table_name: Measured table (e.g. ``"usgs_earthquake"``).
        file_date: Snapshot date or ``"overall"``.
        metric: Metric name (e.g. ``"bad_row_pct"``, ``"null_pct__mag"``).
        value: Metric value.
        computed_at: When the metric was computed.
    """

    table_name: str = Field(sa_column=Column("table_name", String, primary_key=True, nullable=False))
    file_date: str = Field(sa_column=Column("file_date", String, primary_key=True, nullable=False))
    metric: str = Field(sa_column=Column("metric", String, primary_key=True, nullable=False))
    value: float = Field(sa_column=Column("value", Float, nullable=False))
    computed_at: dt.datetime = Field(sa_column=Column("computed_at", DateTime, nullable=False))

    __tablename__ = "data_quality"
    __table_args__ = {"schema": "geo"}

    # ConfigDict instead of SQLModelConfig: this sqlmodel build has no SQLModelConfig
    # and the legacy `class Config` is a pydantic v2 deprecation.
    model_config = ConfigDict(  # type: ignore[assignment]
        json_schema_extra={
            "example": {
                "table_name": "avalanche_org",
                "file_date": "overall",
                "metric": "bad_row_pct",
                "value": 0.0,
                "computed_at": "2026-09-21T02:15:00",
            }
        }
    )
