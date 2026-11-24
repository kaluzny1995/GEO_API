# Memory leaks investigation 2026-11-24

## Memory leaks investigation 2026-11-24

### Symptom

Host memory was **33 % before the 2026-11-24 pipeline run and 35.2 % after it**
(+~1.4 GiB on a 62.5 GiB host). This is a follow-up to the 2026-11-23
investigation; it checks whether the daily run left memory in GEO_API.

### Finding

GEO_API is not the cause. The API container held **105.4 MiB** after the run,
down from its previous measurement, with no request-driven growth:

| Measurement | Value |
|-------------|------:|
| API container `docker stats` | 105.4 MiB / 1 GiB |
| Host used (`free`) | 22.0 GiB (35.2 %) |
| `gnome-system-monitor` | 10.65 GiB, +0.87 GiB since 23 Nov |
| Chrome | 6.54 GiB, +0.21 GiB since 23 Nov |
| All nine GEO containers | 1.95 GiB |

The desktop processes account for most of the increase. `gnome-system-monitor`
continued its ~1.1 GiB/day linear growth after the previous investigation.

The daily run itself moved host memory from **21.43 GiB at 07:00 to 21.57 GiB
at 07:22** and then returned to baseline. No live task subprocess remained.

### Code status

No new leak and no code change today. Yesterday's bounded/recycled async pool
(`database` block in `config.json`) is deployed and the container remains far
below its 1 GiB limit. The 2026-11-23 investigation remains the reference for
the API stress test and pool hardening.

### Verification

```bash
cd GEO_API
conda run -n geo_api_311 python -m pytest -q
docker stats --no-stream geo_e2e-geo_fastapi-1
```

### Conclusion

GEO_API is stable across the daily run. The host increase is the desktop
session, primarily `gnome-system-monitor`; closing or restarting it releases
the growth. After the monitor exited at ~18:44, host used fell from 22.0 GiB (35.2 %) to 11.1 GiB (17.6 %), confirming the attribution. Full evidence is in
[GEO_E2E — Memory leaks investigation 2026-11-24](../../GEO_E2E/docs/memory-leaks-investigation-2026-11-24.md).
