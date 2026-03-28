#!/usr/bin/env python3
"""
Production load test for api-accelerator.aiesec.org.eg
Ramps concurrency from 10 → 500 to find the sweet spot.
"""

import asyncio
import random
import time
import statistics
import sys
from dataclasses import dataclass, field
from typing import List

import httpx

BASE_URL = "https://api-accelerator.aiesec.org.eg"
TEST_PATH = "/api/v1/leads/?home_lc_id="
HEALTH_PATH = "/api/v1/health"

# All LC IDs to rotate through — each request picks one at random
HOME_LC_IDS = [
    2820, 1788, 1322, 1789, 899, 1489, 2126, 1064, 109,
    5688, 257, 2124, 171, 1727, 2125, 2817, 2818, 15,
    1725, 1114, 6683,
]

# Concurrency levels to test
LEVELS = [10, 25, 50, 100, 150, 200, 250, 300, 400, 500]
DURATION_PER_LEVEL = 15  # seconds per level
TIMEOUT = 30.0


@dataclass
class LevelResult:
    concurrency: int = 0
    total: int = 0
    success: int = 0
    errors: int = 0
    timeouts: int = 0
    status_codes: dict = field(default_factory=dict)
    latencies: List[float] = field(default_factory=list)
    rps: float = 0.0
    avg_ms: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    error_rate: float = 0.0


async def worker(
    client: httpx.AsyncClient,
    result: LevelResult,
    stop_event: asyncio.Event,
):
    while not stop_event.is_set():
        lc_id = random.choice(HOME_LC_IDS)
        url = f"{BASE_URL}{TEST_PATH}{lc_id}"
        t0 = time.perf_counter()
        try:
            resp = await client.get(url, timeout=TIMEOUT)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            result.total += 1
            result.latencies.append(elapsed_ms)
            code = resp.status_code
            result.status_codes[code] = result.status_codes.get(code, 0) + 1
            if 200 <= code < 400:
                result.success += 1
            else:
                result.errors += 1
        except httpx.TimeoutException:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            result.total += 1
            result.timeouts += 1
            result.errors += 1
            result.latencies.append(elapsed_ms)
        except Exception:
            result.total += 1
            result.errors += 1


async def run_level(concurrency: int, duration: int) -> LevelResult:
    result = LevelResult(concurrency=concurrency)
    stop_event = asyncio.Event()

    limits = httpx.Limits(
        max_connections=concurrency + 50,
        max_keepalive_connections=concurrency,
    )
    async with httpx.AsyncClient(
        http2=True,
        limits=limits,
        verify=True,
        follow_redirects=True,
    ) as client:
        tasks = [
            asyncio.create_task(worker(client, result, stop_event))
            for _ in range(concurrency)
        ]

        await asyncio.sleep(duration)
        stop_event.set()
        await asyncio.gather(*tasks, return_exceptions=True)

    if result.total > 0:
        result.rps = round(result.total / duration, 2)
        result.error_rate = round((result.errors / result.total) * 100, 2)
    if result.latencies:
        sorted_lat = sorted(result.latencies)
        result.avg_ms = round(statistics.mean(sorted_lat), 2)
        result.p50_ms = round(sorted_lat[int(len(sorted_lat) * 0.50)], 2)
        result.p95_ms = round(sorted_lat[int(len(sorted_lat) * 0.95)], 2)
        result.p99_ms = round(sorted_lat[min(int(len(sorted_lat) * 0.99), len(sorted_lat) - 1)], 2)

    return result


def print_header():
    print(f"\n{'='*100}")
    print(f"  PRODUCTION LOAD TEST — {BASE_URL}")
    print(f"  Path: {TEST_PATH}<random_lc_id>")
    print(f"  LC IDs ({len(HOME_LC_IDS)}): {HOME_LC_IDS}")
    print(f"  Duration per level: {DURATION_PER_LEVEL}s")
    print(f"  Levels: {LEVELS}")
    print(f"{'='*100}\n")
    print(
        f"{'Conc':>6} | {'Total':>7} | {'OK':>7} | {'Err':>5} | {'Tout':>5} | "
        f"{'Err%':>6} | {'RPS':>8} | {'Avg ms':>9} | {'P50 ms':>9} | "
        f"{'P95 ms':>9} | {'P99 ms':>9} | {'Codes'}"
    )
    print("-" * 120)


def print_row(r: LevelResult):
    codes_str = " ".join(f"{k}:{v}" for k, v in sorted(r.status_codes.items()))
    print(
        f"{r.concurrency:>6} | {r.total:>7} | {r.success:>7} | {r.errors:>5} | "
        f"{r.timeouts:>5} | {r.error_rate:>5}% | {r.rps:>8} | {r.avg_ms:>9} | "
        f"{r.p50_ms:>9} | {r.p95_ms:>9} | {r.p99_ms:>9} | {codes_str}"
    )


def print_summary(results: List[LevelResult]):
    print(f"\n{'='*100}")
    print("  SUMMARY & RECOMMENDATION")
    print(f"{'='*100}\n")

    # Find sweet spot: highest concurrency with <5% error rate AND p95 < 5000ms
    sweet_spot = None
    for r in results:
        if r.error_rate < 5.0 and r.p95_ms < 5000 and r.success > 0:
            sweet_spot = r

    # Find max viable: <10% error rate
    max_viable = None
    for r in results:
        if r.error_rate < 10.0 and r.success > 0:
            max_viable = r

    # Find breaking point: first level with >20% errors
    breaking = None
    for r in results:
        if r.error_rate > 20.0:
            breaking = r
            break

    if sweet_spot:
        print(f"  ✅ SWEET SPOT:      {sweet_spot.concurrency} concurrent users")
        print(f"     RPS: {sweet_spot.rps} | P95: {sweet_spot.p95_ms}ms | Errors: {sweet_spot.error_rate}%")
    else:
        print("  ⚠️  No sweet spot found (all levels had >5% errors or P95 > 5s)")

    if max_viable:
        print(f"\n  🟡 MAX VIABLE:      {max_viable.concurrency} concurrent users")
        print(f"     RPS: {max_viable.rps} | P95: {max_viable.p95_ms}ms | Errors: {max_viable.error_rate}%")

    if breaking:
        print(f"\n  🔴 BREAKING POINT:  {breaking.concurrency} concurrent users")
        print(f"     RPS: {breaking.rps} | P95: {breaking.p95_ms}ms | Errors: {breaking.error_rate}%")

    peak_rps = max(results, key=lambda r: r.rps)
    print(f"\n  📈 PEAK RPS:        {peak_rps.rps} (at {peak_rps.concurrency} concurrency)")

    print(f"\n{'='*100}")


async def main():
    print_header()

    # Health check first
    try:
        async with httpx.AsyncClient(verify=True, follow_redirects=True) as c:
            resp = await c.get(f"{BASE_URL}{HEALTH_PATH}", timeout=10)
            if resp.status_code >= 400:
                print(f"❌ Health check failed: {resp.status_code}")
                sys.exit(1)
            print(f"✅ Health check passed ({resp.status_code})\n")
    except Exception as e:
        print(f"❌ Cannot reach {BASE_URL}: {e}")
        sys.exit(1)

    results: List[LevelResult] = []

    for level in LEVELS:
        print(f"\n▶ Testing concurrency={level} for {DURATION_PER_LEVEL}s ...", end="", flush=True)
        r = await run_level(level, DURATION_PER_LEVEL)
        results.append(r)
        print(" done")
        print_row(r)

        # Stop early if catastrophic failure
        if r.error_rate > 50 and level > 50:
            print(f"\n⛔ Stopping: error rate {r.error_rate}% at concurrency {level}")
            break

        # Brief cooldown between levels
        await asyncio.sleep(3)

    print_summary(results)


if __name__ == "__main__":
    asyncio.run(main())