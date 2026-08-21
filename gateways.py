"""Both networks behind one helper."""
from __future__ import annotations

import os

GATEWAYS = {
    "isp": "isp.quanticdata.io:8000",
    "residential": "resi.quanticdata.io:8080",
    "residential_premium": "pr.quanticdata.io:7777",
    "socks5": "resi.quanticdata.io:1080",
}

USER = os.environ.get("QD_PROXY_USER") or ""
PASS = os.environ.get("QD_PROXY_PASS") or ""
if not (USER and PASS):
    raise SystemExit("set QD_PROXY_USER and QD_PROXY_PASS")


def username(country: str | None = None, city: str | None = None,
             session: str | None = None, minutes: int | None = None) -> str:
    parts = [USER]
    if country:
        parts += ["country", country]
    if city:
        parts += ["city", city]
    if session:
        parts += ["session", session]
    if minutes:
        parts += ["sessTime", str(minutes)]
    return "-".join(parts)


def proxies(network: str = "residential", scheme: str = "http", **targeting) -> dict[str, str]:
    """A requests-style proxies dict.

    No `session` means a new exit per request — right for monitoring.
    A `session` plus `minutes` pins one exit — required for any cart or queue flow.
    """
    url = f"{scheme}://{username(**targeting)}:{PASS}@{GATEWAYS[network]}"
    return {"http": url, "https": url}
