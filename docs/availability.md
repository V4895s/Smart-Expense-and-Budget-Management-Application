# Availability and performance notes (SEA-NF-001, SEA-NF-002)

## Availability (99.9% monthly)
- `GET /health` checks the database (`SELECT 1`). 200 = healthy, 503 = database unreachable.
- Database engine fails fast (10 s connect/pool timeout) and recycles connections every 5 minutes.
- Database errors return 503 + `Retry-After`; unexpected errors return 500; every error uses the
  `{ code, message }` envelope (the legacy `detail` field is kept for the frontend).
- `.github/workflows/uptime-check.yml` pings `/health` every 30 minutes. Set the repository
  variable `API_HEALTH_URL`. For finer checks, add the same URL to UptimeRobot (free, 5-minute interval).
- Frontend shows a friendly "service unavailable" message when the API cannot be reached (SRS 3.4).
- Monthly uptime = successful checks / total checks, excluding scheduled maintenance.

## Performance (p90 <= 5 s)
- Every response carries `X-Process-Time`; requests over 5 s are logged as `SLOW`.
- Composite indexes: run `backend/migrations/20261106_transaction_indexes.sql` on Supabase.
- `GET /transactions` supports filtering and `limit`/`offset` pagination.
- Load test: `python backend/scripts/load_test.py --token <JWT> --out docs/perf-results.md`.
