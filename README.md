# Sneaker proxy setup — ISP for speed, residential for the queue

Two networks, two jobs, and the reason people get this wrong:

| | [ISP proxies](https://quanticdata.io/isp-proxies/) | [Residential](https://quanticdata.io/cheap-residential-proxies/) |
|---|---|---|
| Gateway | `isp.quanticdata.io:8000` | `resi.quanticdata.io:8080` |
| Hosted in | a datacenter, on an ISP-registered range | real consumer connections |
| Latency | low and stable | higher and variable |
| IP looks like | a residential ISP customer | a residential ISP customer |
| Billing | per IP | per GB |
| Use it for | checkout speed, monitoring | the queue, account pages, anything patient |

Speed matters at exactly one moment. Everything before that moment is patience, and paying ISP
prices for patience is how people burn a budget before the drop.

See also [sneaker proxies](https://quanticdata.io/sneaker-proxies/).

```bash
export QD_PROXY_USER=your_user QD_PROXY_PASS=your_pass

python3 latency_bench.py --country us --n 20     # measure before you commit
python3 stock_monitor.py products.json           # residential, patient, cheap
bash preflight.sh                                # the 60-second sanity check
```

## Files

| File | What it does |
|---|---|
| [`gateways.py`](gateways.py) | both networks, the username modifiers, one helper |
| [`latency_bench.py`](latency_bench.py) | p50/p95 latency and success rate, ISP vs residential |
| [`stock_monitor.py`](stock_monitor.py) | jittered availability polling on residential exits |
| [`preflight.sh`](preflight.sh) | credentials, geo, rotation and sticky, checked in one pass |

## Sticky sessions are not optional here

Any flow with a cart, a login or a queue position must stay on one exit. Change IP mid-flow and
you look like a hijacked session, which is the fastest way to lose the position you waited for.

```bash
# one exit for 30 minutes
curl -x isp.quanticdata.io:8000 \
     -U "USER-country-us-session-drop01-sessTime-30:PASS" https://ipinfo.io/json
```

Pick the session token per *task*, not per request: one token per checkout attempt, held for the
whole attempt. `stock_monitor.py` shows the opposite pattern — no session at all, because
monitoring wants a fresh IP every poll.

## Polling politely, and why it is in your interest

`stock_monitor.py` jitters its interval and backs off on 429 and 403. That is not decoration:

- A fixed interval is a signature. Twelve requests exactly 30 seconds apart is not a shopper.
- Hammering a product page gets the IP range flagged, which costs you the drop you were waiting
  for.
- Backing off on a 429 preserves the exit; ignoring it burns it.

## What this repo will not do

There is no queue-jumping, no CAPTCHA solving, no automated purchasing, and no advice on
evading a retailer's per-customer limits here. This is proxy configuration and availability
monitoring. Read the terms of the site you are targeting, and check
[robots.txt](https://quanticdata.io/tools/robots-txt-tester/) before you point anything at it.

## Related

- [Sneaker proxies](https://quanticdata.io/sneaker-proxies/) · [ISP proxies](https://quanticdata.io/isp-proxies/) · [Cheap residential proxies](https://quanticdata.io/cheap-residential-proxies/)
- [Proxy quickstart](https://github.com/quantumproxies/quanticdata-proxy-quickstart) · [How to use rotating proxies](https://quanticdata.io/blog/how-to-use-rotating-proxies/)
- [How to detect residential proxies](https://quanticdata.io/blog/how-to-detect-residential-proxies/)

MIT licensed.
