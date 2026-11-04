"""CSV metadata written by the PySpark DATA_SOURCE_FILE job.

GEO_API serves ``geo.data_source_files`` (one row per real CSV) and
``geo.data_source_sources`` (one row per source folder, kept separately so a
source with no files still appears in the dropdown). The file listing is
produced on the Spark side, so the API container never needs the GEO_Download
data folder.
"""

from pydantic import BaseModel, ConfigDict
from sqlmodel import Column, Field, Float, Integer, SQLModel, String


class DataSourceFile(SQLModel, table=True):
    """One real CSV snapshot row in ``geo.data_source_files``.

    Attributes:
        source_name: Source folder name (e.g. ``"EONET"``).
        file_name: CSV file name.
        snapshot_date: ``YYYY-MM-DD`` parsed from the file name, if any.
        created_at: Filesystem modification time as ISO-8601 UTC text.
        records: Data rows excluding the header and blank lines.
        size_kb: File size in 1024-byte kilobytes, rounded to one decimal.
        pipeline_start_date: Earliest enabled source start date at publication
            time (the canonical copy lives in ``geo.data_source_sources``).
    """

    source_name: str = Field(sa_column=Column("source_name", String, primary_key=True, nullable=False))
    file_name: str = Field(sa_column=Column("file_name", String, primary_key=True, nullable=False))
    snapshot_date: str | None = Field(default=None, sa_column=Column("snapshot_date", String, nullable=True))
    created_at: str = Field(sa_column=Column("created_at", String, nullable=False))
    records: int = Field(sa_column=Column("records", Integer, nullable=False))
    size_kb: float = Field(sa_column=Column("size_kb", Float, nullable=False))
    pipeline_start_date: str | None = Field(
        default=None, sa_column=Column("pipeline_start_date", String, nullable=True)
    )

    __tablename__ = "data_source_files"
    __table_args__ = {"schema": "geo"}

    model_config = ConfigDict(  # type: ignore[assignment]
        json_schema_extra={
            "example": {
                "source_name": "EONET",
                "file_name": "eonet_events_2026-09-01.csv",
                "snapshot_date": "2026-09-01",
                "created_at": "2026-10-04T02:14:50Z",
                "records": 12,
                "size_kb": 0.7,
                "pipeline_start_date": "2026-09-01",
            }
        }
    )


class DataSourceSource(SQLModel, table=True):
    """One source folder row in ``geo.data_source_sources``.

    Kept separately from the file rows so ``geo.data_source_files`` contains
    real CSV files only, while a source with no current files still appears in
    the API's source list.

    Attributes:
        source_name: Source folder name (e.g. ``"EONET"``).
        pipeline_start_date: Earliest enabled source start date from
            GEO_Download's ``config.json``.
        updated_at: When the source row was last refreshed (ISO-8601 UTC).
    """

    source_name: str = Field(sa_column=Column("source_name", String, primary_key=True, nullable=False))
    pipeline_start_date: str | None = Field(
        default=None, sa_column=Column("pipeline_start_date", String, nullable=True)
    )
    updated_at: str = Field(sa_column=Column("updated_at", String, nullable=False))

    __tablename__ = "data_source_sources"
    __table_args__ = {"schema": "geo"}

    model_config = ConfigDict(  # type: ignore[assignment]
        json_schema_extra={
            "example": {
                "source_name": "EONET",
                "pipeline_start_date": "2026-09-01",
                "updated_at": "2026-11-03T22:16:58Z",
            }
        }
    )


class DataSourceFileInfo(BaseModel):
    """File metadata returned by the API (without the repeated pipeline start date)."""

    model_config = ConfigDict(frozen=True)

    source_name: str
    file_name: str
    snapshot_date: str | None
    created_at: str
    records: int
    size_kb: float


class DataSourceFilesResponse(BaseModel):
    """Source names, configured start date and all CSV file metadata.

    Attributes:
        start_date: Earliest ``pipeline_start_date`` published by GEO_ETL.
        latest_date: Latest snapshot date found across all CSV files.
        sources: Source folder names, sorted alphabetically.
        files: Metadata of every CSV file.
    """

    model_config = ConfigDict(frozen=True)

    start_date: str | None
    latest_date: str | None
    sources: list[str]
    files: list[DataSourceFileInfo]
