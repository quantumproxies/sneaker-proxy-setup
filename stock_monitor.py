"""Availability polling on residential exits — jittered, backing off, cheap.

No session token: every poll gets a fresh IP, which is exactly what you want when
you are not holding any state. The jitter and the backoff are what keep the range
usable until the moment it matters.

    python3 stock_monitor.py products.json --interval 45
    # products.json: [{"name":"…","url":"https://…","in_stock_when":"add to cart"}]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import time
from datetime import datetime

import requests

from gateways import proxies

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")


def check(product: dict, country: str) -> tuple[bool | None, str]:
    try:
        r = requests.get(product["url"], proxies=proxies("residential", country=country),
                         headers={"User-Agent": UA}, timeout=40)
    except requests.RequestException as exc:
        return None, type(exc).__name__

    if r.status_code in (403, 429):
        return None, f"HTTP {r.status_code}"
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"

    body = r.text.lower()
    needle = (product.get("in_stock_when") or "add to cart").lower()
    blocker = (product.get("out_of_stock_when") or "sold out").lower()
    if blocker in body:
        return False, "sold out"
    return needle in body, "ok"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", type=pathlib.Path)
    ap.add_argument("--country", default="us")
    ap.add_argument("--interval", type=int, default=45, help="base seconds between polls")
    ap.add_argument("--webhook", default=None)
    args = ap.parse_args()

    products = json.loads(args.file.read_text(encoding="utf-8"))
    state: dict[str, bool | None] = {}
    penalty = 0.0

    while True:
        for product in products:
            available, note = check(product, args.country)
            stamp = datetime.now().strftime("%H:%M:%S")
            was = state.get(product["name"])

            if note.startswith("HTTP 4"):
                # Backing off preserves the exit range. Ignoring a 429 burns it.
                penalty = min(penalty * 2 + 30, 600)
                print(f"{stamp}  {product['name'][:30]:<32}{note}  backing off {penalty:.0f}s")
            else:
                penalty = max(0.0, penalty / 2)
                print(f"{stamp}  {product['name'][:30]:<32}"
                      f"{'IN STOCK' if available else 'out' if available is False else note}")

            if available and was is not True:
                message = f"IN STOCK: {product['name']} — {product['url']}"
                print(f"  *** {message}")
                if args.webhook:
                    try:
                        requests.post(args.webhook, json={"text": message}, timeout=10)
                    except requests.RequestException:
                        pass
            state[product["name"]] = available

        # Jitter: a fixed interval is a signature, not a shopper.
        wait = args.interval * random.uniform(0.7, 1.4) + penalty
        time.sleep(wait)


if __name__ == "__main__":
    main()
