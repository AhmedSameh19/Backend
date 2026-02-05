from __future__ import annotations

import argparse
import asyncio
import random
import statistics
import time
from dataclasses import dataclass
from typing import Optional

import httpx


@dataclass
class Result:
    ok: bool
    status_code: int
    latency_ms: float


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    if p <= 0:
        return min(values)
    if p >= 100:
        return max(values)
    values_sorted = sorted(values)
    k = (len(values_sorted) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(values_sorted) - 1)
    if f == c:
        return values_sorted[f]
    d0 = values_sorted[f] * (c - k)
    d1 = values_sorted[c] * (k - f)
    return d0 + d1


async def worker(
    worker_id: int,
    client: httpx.AsyncClient,
    stop_at: float,
    path: str,
    home_lc_id: Optional[int],
    think_time_ms: int,
    results: list[Result],
) -> None:
    rng = random.Random(worker_id)
    while time.perf_counter() < stop_at:
        url = path
        if "{home_lc_id}" in url:
            if home_lc_id is None:
                raise ValueError("home_lc_id is required for this path")
            url = url.replace("{home_lc_id}", str(home_lc_id))

        start = time.perf_counter()
        try:
            resp = await client.get(url)
            latency_ms = (time.perf_counter() - start) * 1000.0
            ok = 200 <= resp.status_code < 400
            results.append(Result(ok=ok, status_code=resp.status_code, latency_ms=latency_ms))
        except Exception:
            latency_ms = (time.perf_counter() - start) * 1000.0
            results.append(Result(ok=False, status_code=0, latency_ms=latency_ms))

        if think_time_ms > 0:
            await asyncio.sleep(rng.uniform(0, think_time_ms / 1000.0))


async def run(
    base_url: str,
    path: str,
    concurrency: int,
    duration_s: int,
    home_lc_id: Optional[int],
    timeout_s: float,
    think_time_ms: int,
) -> None:
    stop_at = time.perf_counter() + duration_s
    limits = httpx.Limits(max_keepalive_connections=concurrency, max_connections=concurrency)

    async with httpx.AsyncClient(
        base_url=base_url.rstrip("/"),
        timeout=httpx.Timeout(timeout_s),
        limits=limits,
    ) as client:
        results: list[Result] = []
        tasks = [
            asyncio.create_task(
                worker(
                    worker_id=i,
                    client=client,
                    stop_at=stop_at,
                    path=path,
                    home_lc_id=home_lc_id,
                    think_time_ms=think_time_ms,
                    results=results,
                )
            )
            for i in range(concurrency)
        ]
        await asyncio.gather(*tasks)

    latencies = [r.latency_ms for r in results]
    ok_count = sum(1 for r in results if r.ok)
    err_count = len(results) - ok_count
    rps = len(results) / max(duration_s, 1)

    print("=== Load Test Results ===")
    print(f"Base URL: {base_url}")
    print(f"Path: {path}")
    print(f"Concurrency: {concurrency}")
    print(f"Duration: {duration_s}s")
    if home_lc_id is not None:
        print(f"home_lc_id: {home_lc_id}")
    print(f"Total requests: {len(results)}")
    print(f"Success: {ok_count}")
    print(f"Errors: {err_count}")
    print(f"RPS: {rps:.2f}")
    if latencies:
        print(f"Latency avg: {statistics.mean(latencies):.2f} ms")
        print(f"Latency p50: {percentile(latencies, 50):.2f} ms")
        print(f"Latency p95: {percentile(latencies, 95):.2f} ms")
        print(f"Latency p99: {percentile(latencies, 99):.2f} ms")


def main() -> None:
    parser = argparse.ArgumentParser(description="Async load tester for the FastAPI backend")
    parser.add_argument("--base-url", default="https://api-accelerator.aiesec.org.eg", help="Base URL, e.g. https://api-accelerator.aiesec.org.eg")
    parser.add_argument(
        "--path",
        default="/api/v1/health/",
        help="Path to hit (can include {home_lc_id}), e.g. /api/v1/leads/?home_lc_id={home_lc_id}",
    )
    parser.add_argument("--concurrency", type=int, default=50)
    parser.add_argument("--duration", type=int, default=30, help="Duration in seconds")
    parser.add_argument("--home-lc-id", type=int, default=None)
    parser.add_argument("--timeout", type=float, default=10.0, help="Per-request timeout seconds")
    parser.add_argument("--think-time-ms", type=int, default=0, help="Random sleep between requests per worker")

    args = parser.parse_args()

    asyncio.run(
        run(
            base_url=args.base_url,
            path=args.path,
            concurrency=args.concurrency,
            duration_s=args.duration,
            home_lc_id=args.home_lc_id,
            timeout_s=args.timeout,
            think_time_ms=args.think_time_ms,
        )
    )


if __name__ == "__main__":
    main()
