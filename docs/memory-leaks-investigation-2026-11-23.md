# Memory leaks investigation 2026-11-23

## Memory leaks investigation 2026-11-23

### Symptom

The GEO stack had been running since 2026-11-17 without a task error, but the host
memory reported in the Airflow task callbacks grew from **11.92 GiB on 17 November
to 19.63 GiB on 23 November** — about **1.3 GiB per day**. The user-reported range
was 8.7 → 22.2 GiB across the full run.

### Root cause

The growth was **not in the six GEO repositories**. It was traced to the desktop
session on the same host:

| Measurement (2026-11-23) | Value |
|--------------------------|-------|
| Host used memory | 19.63 GiB / 62.50 GiB |
| `gnome-system-monitor` RSS | 9.74 GiB |
| `gnome-system-monitor` growth | ~12–15 KiB/s → **~1.1 GiB/day** |
| Chrome processes (all renderers) | ~6.3 GiB |
| Nine GEO containers (all cgroups, incl. page cache) | ~3.0–3.4 GiB |
| GEO containers, `docker stats` (cache excluded) | ~2.6 GiB |

`gnome-system-monitor` had been running since boot and has a known history-buffer
growth problem; after nine days it alone held about half of the host's anonymous
memory. The GEO containers were bounded by their Compose limits and did not grow.

### GEO_API audit

* The provider is a process-wide singleton (`get_provider()`); the endpoint
  dependencies create only light wrappers around it, never a second engine.
* Every `run_select_statement` / `run_insert_statement` uses an `AsyncSession`
  context manager, so the connection returns to the pool on success and on error.
* The API stress test sent 1,000 requests across `/health`,
  `/data-quality/*`, `/event-counts/*` and `/data-source-files`: RSS moved from
  **89.5 to 93.2 MiB (+3.7 MiB)**, and a longer run plateaued around 94 MiB —
  allocator noise, not a per-request leak.
* Endpoint loggers are created once per route, not per request, and the file
  handlers are idempotent (`util.setup_logger` already had the leak regression
  test from the October memory work).

No unbounded cache, module-level list or unclosed session was found.

### Change made

Even though the host growth is external, the long-lived API should not keep
pooled connections forever: Supabase's pooler reaps idle connections, and a
pool that only grows is indistinguishable from a connection leak. The shared
async engine is now explicitly bounded and recycled:

```python
create_async_engine(
    url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    pool_recycle=300,
    ...,
)
```

The options live in the `database` block of `config.json`
(`pool_size`, `max_overflow`, `pool_recycle_seconds`) and the provider
constructor accepts the same three values for tests or deployments that build
the provider directly. Tests assert the config wiring and the overrides in
`test/provider/supabase_postgres/test_supabase_postgres_provider.py`.

### Verification

```bash
# API RSS is flat under repeated requests
for i in $(seq 1 1000); do
  curl -s -o /dev/null 'http://localhost:8000/event-counts/location?limit=10000'
done
docker exec geo_e2e-geo_fastapi-1 grep VmRSS /proc/23/status

# Host attribution: the GEO containers are a small, stable slice
docker stats --no-stream
ps -eo pid,rss,comm --sort=-rss | head
```

### Conclusion

GEO_API is not the source of the multi-gigabyte daily growth. The added pool
bounds make the API's own memory/connection lifetime explicit and testable;
the host-level leak was the desktop system monitor (and Chrome), not this
service.
