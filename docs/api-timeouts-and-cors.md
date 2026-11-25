# API timeouts, CORS and Supabase pooling

## Symptom (2026-11-25)

The React dashboard showed **“API server is down! Please check the API server.”**
in several views. The browser console showed:

```
Access to fetch at 'http://localhost:8000/data-quality/.../file-dates?...'
from origin 'http://localhost:3000' has been blocked by CORS policy:
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

The Chrome-extension warnings in the same console are unrelated.

## Root cause chain

Two independent problems combined into a misleading browser error:

1. **Supabase transaction pooler + asyncpg prepared statements.** The API's
   `pool_pre_ping` uses asyncpg's internal `fetchrow(";")` ping. That path uses
   asyncpg's own default prepared-statement cache (`__asyncpg_stmt_N__`), even
   though SQLAlchemy's `prepared_statement_cache_size` was already zero. The
   Supabase pooler moves a client between server connections, so those named
   statements disappear or collide. The API log showed:
   `prepared statement "__asyncpg_stmt_11b__" does not exist` and
   `prepared statement ... already exists`.
2. **Unhandled 500 responses had no CORS header.** Starlette's
   `ServerErrorMiddleware` is outside `CORSMiddleware`; an unhandled exception
   became a plain-text 500 without `Access-Control-Allow-Origin`. The browser
   therefore reported a CORS failure, and the app classified it as “API down”.

A third issue made the failure more likely: the 100-date IBTrACS probe returns
**29,049 rows / ~4.1 MB** and took **5–9 s** under concurrent requests. The
client's old **8 s** timeout aborted requests right at the edge, which also
looks like the API being down.

## Fixes

### GEO_API

`provider/supabase_postgres/supabase_postgres_provider.py` now passes both
asyncpg cache controls:

```python
connect_args = {
    "statement_cache_size": 0,
    "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
}
```

`statement_cache_size=0` disables asyncpg's internal cache (used by the ping);
the URL's `prepared_statement_cache_size=0` disables SQLAlchemy's cache; the
unique name function still protects the main statements from PgBouncer name
collisions.

`error_handlers.InternalServerErrorMiddleware` catches unhandled route errors
**inside** CORS and returns the standard JSON 500 envelope. It is registered
before `CORSMiddleware` so CORS decorates the response with the correct header.

### GEO_APP

`src/config.js` raises `API_TIMEOUT_MS` from **8 s to 30 s**. The data-quality
probe is a multi-megabyte query; a 30 s budget avoids aborting a request that
the API is still serving. Smaller endpoints still return in milliseconds.

## Verification

```bash
# API: concurrent date probes all return 200 after the fix
seq 1 8 | xargs -P8 -I{} curl -s -o /dev/null -w '%{http_code}\n' \
  'http://localhost:8000/data-quality/ibtracs_cyclone/file-dates?file_dates=...'

# CORS header present on successful and error responses
curl -s -D - -o /dev/null -H 'Origin: http://localhost:3000' \
  'http://localhost:8000/data-quality/tables'

# API test suite
cd GEO_API && conda run -n geo_api_311 python -m pytest -q
```

Three waves of eight concurrent `file-dates` requests returned **24/24 HTTP
200** responses after the change; the old build produced 500s with the
prepared-statement errors. The new API tests cover the middleware’s 500 + CORS
behavior without leaking the internal exception text.

## Deployment

`geo_fastapi` and `geo_react_app` were rebuilt and recreated. The E2E stack’s
Airflow/Spark services were left untouched because this change does not alter
them.
