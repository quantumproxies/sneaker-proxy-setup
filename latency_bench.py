"""Measure both networks before you decide where the money goes.

Reports success rate, p50 and p95 latency per network. p95 is the number that
matters for a timed event: the median tells you the good case, the tail tells you
what happens on the attempt you actually cared about.

    python3 latency_bench.py --country us --n 20 --url https://ipinfo.io/json
"""
from __future__ import annotations

import argparse
import statistics
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import requests

from gateways import GATEWAYS, proxies

NETWORKS = ["isp", "residential", "residential_premium"]


def attempt(network: str, url: str, country: str) -> dict:
    started = time.perf_counter()
    try:
        r = requests.get(url, proxies=proxies(network, country=country), timeout=45)
        return {"network": network, "status": r.status_code,
                "seconds": time.perf_counter() - started}
    except requests.RequestException as exc:
        return {"network": network, "status": type(exc).__name__,
                "seconds": time.perf_counter() - started}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="https://ipinfo.io/json")
    ap.add_argument("--country", default="us")
    ap.add_argument("--n", type=int, default=15, help="attempts per network")
    args = ap.parse_args()

    jobs = [(n, args.url, args.country) for n in NETWORKS for _ in range(args.n)]
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda j: attempt(*j), jobs))

    print(f"{args.url}   {args.n} attempts per network, exit {args.country.upper()}\n")
    print(f"{'network':<22}{'ok':>8}{'p50 s':>9}{'p95 s':>9}  outcomes")
    summary = {}
    for network in NETWORKS:
        rows = [r for r in results if r["network"] == network]
        good = [r for r in rows if r["status"] == 200]
        times = sorted(r["seconds"] for r in good) or [0]
        p50 = statistics.median(times)
        p95 = times[min(len(times) - 1, int(0.95 * len(times)))]
        summary[network] = (len(good) / len(rows), p50, p95)
        print(f"{network:<22}{len(good):>3}/{len(rows):<4}{p50:>9.2f}{p95:>9.2f}  "
              f"{dict(Counter(r['status'] for r in rows))}")

    isp_rate, isp_p95 = summary['isp'][0], summary['isp'][2]
    res_rate, res_p95 = summary['residential'][0], summary['residential'][2]
    print()
    if isp_rate >= res_rate and isp_p95 < res_p95 * 0.7:
        print(f"ISP is meaningfully faster at the tail ({isp_p95:.2f}s vs {res_p95:.2f}s). "
              "Worth it for the timed step — still use residential for monitoring.")
    elif res_rate > isp_rate:
        print("Residential succeeds more often here. The ISP range may be flagged on this "
              "target; test before the drop, not during it.")
    else:
        print("No meaningful tail difference on this target. Residential is the cheaper "
              "default; keep ISP for the checkout step only.")


if __name__ == "__main__":
    main()
