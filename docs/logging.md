← [README](../README.md)

# Logging

Every endpoint writes to its own log file, following the GEO_ETL / GEO_Download conventions
(`%(asctime)s %(levelname)s %(message)s`, file + stdout mirror via `util.setup_logger`).

- **Path:** `logs/<tag>/<handler>_<first-request timestamp>.log` — for example
  `logs/event_counts/get_event_counts_by_category_2026-10-20T20:08:34.334520.log`, where the
  directory is the router tag (`main`, `data_quality`, `data_quantity`, `data_source_files`,
  `event_counts`).
- **One file per endpoint per application run**, created lazily on the endpoint's first
  request and appended to for every subsequent request — no empty files.
- **Content:** a start line and a finish line per request with status code and elapsed time;
  unhandled errors are logged with a full traceback at the endpoint boundary and re-raised
  (so the global handler can still map them, e.g. `SupabaseServerDownError` → 503); client
  errors (4xx) are logged as warnings without a traceback.
- **Database activity** (endpoints that query Supabase): each successful query adds
  `Connected to Supabase Postgres`, `Executing SQL: <compiled statement> | params={...}` and
  `Returned N records` between the start and finish lines. The Supabase provider logs
  through the calling endpoint's logger (published via a context variable,
  `util.endpoint_logger`), so the exact statement and row count of every query land in the
  endpoint's own file; outside a request the provider falls back to its module logger.
- **Namespaced, non-propagating loggers** (`geo_api.<handler>`): records never double-emit
  through the root logger, and unrelated records (e.g. httpx access lines) never pollute an
  endpoint file.
- The Supabase provider creates **no log file of its own** — its module logger is
  handler-less; connection failures surface in the calling endpoint's log file via the
  boundary traceback.
- Implemented by `routes/logging_route.py` (`LoggingRoute`, an `APIRoute` subclass): every
  router created with `APIRouter(route_class=LoggingRoute)` is covered automatically,
  including endpoints added later.

Example — the full life of one request in
`logs/event_counts/get_event_counts_by_category_<ts>.log`:

```text
2026-10-20 20:08:34,335 INFO GET /event-counts/category started
2026-10-20 20:08:34,338 INFO Connected to Supabase Postgres
2026-10-20 20:08:34,339 INFO Executing SQL: SELECT geo.union_etl.source_name, … count(*) AS count FROM geo.union_etl GROUP BY … ORDER BY … LIMIT 100
2026-10-20 20:08:35,093 INFO Returned 100 records
2026-10-20 20:08:35,094 INFO GET /event-counts/category finished with 200 in 759.3 ms
```
