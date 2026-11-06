"""Simple load test for SEA-NF-001 (TC-Perf-01): p90 response time must be <= 5 s.

Usage (from backend/):
    python scripts/load_test.py --base-url http://127.0.0.1:8000 --token <JWT> \
        --users 50 --requests 400 --out ../docs/perf-results.md

Get a token: POST /auth/login (or /auth/token) -> "access_token" in the response.
Needs only `httpx` (already used by the tests).
"""

import argparse
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import httpx

ENDPOINTS = [
    "/transactions",
    "/transactions?q=food",
    "/transactions?type=expense&limit=50",
    "/budgets",
    "/health",
]
TARGET_P90_SECONDS = 5.0


def percentile(values, pct):
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(pct / 100 * len(ordered)) - 1))
    return ordered[index]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--token", required=True)
    parser.add_argument("--users", type=int, default=50, help="concurrent users")
    parser.add_argument("--requests", type=int, default=400, help="total requests")
    parser.add_argument("--out", help="write a markdown report to this path")
    args = parser.parse_args()

    headers = {"Authorization": f"Bearer {args.token}"}
    timings, failures = [], 0

    def one(i):
        path = ENDPOINTS[i % len(ENDPOINTS)]
        start = time.perf_counter()
        try:
            ok = client.get(args.base_url + path, headers=headers, timeout=30).status_code < 400
        except httpx.HTTPError:
            ok = False
        return time.perf_counter() - start, ok

    with httpx.Client() as client:
        wall = time.perf_counter()
        with ThreadPoolExecutor(max_workers=args.users) as pool:
            for elapsed, ok in pool.map(one, range(args.requests)):
                timings.append(elapsed)
                failures += 0 if ok else 1
        wall = time.perf_counter() - wall

    p50, p90, p99 = (percentile(timings, p) for p in (50, 90, 99))
    passed = p90 <= TARGET_P90_SECONDS and failures == 0
    lines = [
        "# Performance test results (SEA-NF-001 / TC-Perf-01)",
        "",
        f"- Date: {date.today()}",
        f"- Target: {args.base_url}",
        f"- Concurrent users: {args.users}, total requests: {args.requests}",
        f"- Throughput: {args.requests / wall:.1f} req/s",
        f"- Failed requests: {failures}",
        f"- Mean: {statistics.mean(timings):.3f}s | p50: {p50:.3f}s | p90: {p90:.3f}s | p99: {p99:.3f}s",
        f"- Requirement: p90 <= {TARGET_P90_SECONDS:.0f}s -> **{'PASS' if passed else 'FAIL'}**",
    ]
    report = "\n".join(lines)
    print(report)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(report + "\n")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
