"""Aggregated event count rows returned by the event-count endpoints.

Both models are plain response DTOs: one row of ``geo.union_etl`` counts per
distinct combination of the grouping columns. ``count`` is the number of
``geo.union_etl`` rows in the group (``COUNT(*)``); the field order of each
model mirrors the column order of the provider's ``SELECT``.
"""

from pydantic import BaseModel, ConfigDict


class EventCategoryCount(BaseModel):
    """Row counts grouped by source, event taxonomy and danger rating.

    Attributes:
        source_name: Producing system (``AVALANCHE_ORG``, ``GDACS``, …).
        subsource_name: Subsystem that emitted the event — issuing center,
            agency or basin; ``None`` when the source has none.
        event_category: Catastrophe class (``avalanche``, ``cyclone``, …).
        event_subcategory: Catastrophe subtype; ``None`` when the source has
            no subtype.
        danger_rating: Severity on the shared scale (``no_rating``, ``none``,
            ``low``, ``medium``, ``high``, ``extreme``); ``None`` for rows
            loaded by older ETL versions.
        count: Number of ``geo.union_etl`` rows in the group.
    """

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "source_name": "AVALANCHE_ORG",
                "subsource_name": "Bridgeport Avalanche Center",
                "event_category": "avalanche",
                "event_subcategory": None,
                "danger_rating": "no_rating",
                "count": 39,
            }
        },
    )

    source_name: str
    subsource_name: str | None = None
    event_category: str
    event_subcategory: str | None = None
    danger_rating: str | None = None
    count: int


class EventLocationCount(BaseModel):
    """Row counts grouped by source, location and danger rating.

    Attributes:
        source_name: Producing system (``AVALANCHE_ORG``, ``GDACS``, …).
        subsource_name: Subsystem that emitted the event — issuing center,
            agency or basin; ``None`` when the source has none.
        country_code: ISO 3166-1 alpha-2 country code.
        state_province: ISO 3166-2 subdivision code; ``None`` when the source
            has no subdivision.
        danger_rating: Severity on the shared scale (``no_rating``, ``none``,
            ``low``, ``medium``, ``high``, ``extreme``); ``None`` for rows
            loaded by older ETL versions.
        count: Number of ``geo.union_etl`` rows in the group.
    """

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "source_name": "AVALANCHE_ORG",
                "subsource_name": "Bridgeport Avalanche Center",
                "country_code": "US",
                "state_province": "CA",
                "danger_rating": "no_rating",
                "count": 39,
            }
        },
    )

    source_name: str
    subsource_name: str | None = None
    country_code: str
    state_province: str | None = None
    danger_rating: str | None = None
    count: int
