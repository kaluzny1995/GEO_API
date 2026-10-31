"""Data quantity contracts — actual row counts of the tracked GEO tables.

The data-quantity view needs the **database** row count of every tracked table
for a snapshot, not the ``total_records`` metric stored in ``geo.data_quality``
(that metric is computed by GEO_ETL and can lag behind later backfills). The
provider runs a ``COUNT(*)`` per table, so the response always matches the
table's current contents.

``TABLE_NAMES`` mirrors ``TABLE_NAMES`` in GEO_APP's ``src/config.js``: nine
plain source tables, their nine ``*_etl`` tables and ``union_etl``. Keep the two
lists in sync when a dataset is added.
"""

from pydantic import BaseModel, ConfigDict

OVERALL_FILE_DATE = "overall"

TABLE_NAMES: tuple[str, ...] = (
    # Plain data source tables (9)
    "eonet_event",
    "nifc_fire",
    "ibtracs_cyclone",
    "usgs_earthquake",
    "usgs_volcano",
    "openmeteo_flood",
    "gdacs_event",
    "usgs_nwis",
    "avalanche_org",
    # ETL tables (9)
    "eonet_event_etl",
    "nifc_fire_etl",
    "ibtracs_cyclone_etl",
    "usgs_earthquake_etl",
    "usgs_volcano_etl",
    "openmeteo_flood_etl",
    "gdacs_event_etl",
    "usgs_nwis_etl",
    "avalanche_org_etl",
    # Union table (1)
    "union_etl",
)


class TableCount(BaseModel):
    """Row count of one tracked table for one snapshot.

    Attributes:
        table_name: Tracked table name (e.g. ``"usgs_earthquake"``).
        file_date: Snapshot date (``YYYY-MM-DD``) or ``"overall"`` for the
            whole table.
        count: Number of rows in the table for that snapshot.
    """

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "table_name": "usgs_earthquake",
                "file_date": "2026-10-26",
                "count": 16599,
            }
        },
    )

    table_name: str
    file_date: str
    count: int
