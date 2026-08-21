#!/usr/bin/env bash
# Sixty seconds of checks that prevent the four support tickets people file at 09:59.
#   QD_PROXY_USER=... QD_PROXY_PASS=... bash preflight.sh [country]
set -uo pipefail
: "${QD_PROXY_USER:?set QD_PROXY_USER}"
: "${QD_PROXY_PASS:?set QD_PROXY_PASS}"

COUNTRY="${1:-us}"
U="$QD_PROXY_USER"
P="$QD_PROXY_PASS"
CHECK=https://ipinfo.io/json

fail=0

echo "1. credentials"
for gw in "isp isp.quanticdata.io:8000" "residential resi.quanticdata.io:8080"; do
  set -- $gw
  code=$(curl -s -o /dev/null -m 30 -w '%{http_code}' -x "$2" -U "$U-country-$COUNTRY:$P" "$CHECK")
  if [ "$code" = "200" ]; then
    printf "   %-14s ok\n" "$1"
  else
    printf "   %-14s FAIL (HTTP %s — 407 means bad credentials or the plan does not cover this network)\n" "$1" "$code"
    fail=1
  fi
done

echo
echo "2. geo (asked for ${COUNTRY^^})"
got=$(curl -s -m 30 -x isp.quanticdata.io:8000 -U "$U-country-$COUNTRY:$P" "$CHECK" \
      | tr -d ' "' | grep -o 'country:[A-Z]*' | cut -d: -f2)
if [ "$got" = "${COUNTRY^^}" ]; then
  echo "   ok — exit reports $got"
else
  echo "   MISMATCH — asked ${COUNTRY^^}, got '${got:-none}'. Use ISO 3166-1 alpha-2 (gb, not uk)."
  fail=1
fi

echo
echo "3. rotation (no session → should differ)"
a=$(curl -s -m 30 -x resi.quanticdata.io:8080 -U "$U-country-$COUNTRY:$P" "$CHECK" | grep -o '"ip":"[^"]*"')
b=$(curl -s -m 30 -x resi.quanticdata.io:8080 -U "$U-country-$COUNTRY:$P" "$CHECK" | grep -o '"ip":"[^"]*"')
[ "$a" != "$b" ] && echo "   ok — $a then $b" || { echo "   WARNING — same IP twice; is a -session- left in your username?"; }

echo
echo "4. sticky (session → should match)"
S=$(head -c4 /dev/urandom | xxd -p)
c=$(curl -s -m 30 -x isp.quanticdata.io:8000 -U "$U-country-$COUNTRY-session-$S-sessTime-30:$P" "$CHECK" | grep -o '"ip":"[^"]*"')
d=$(curl -s -m 30 -x isp.quanticdata.io:8000 -U "$U-country-$COUNTRY-session-$S-sessTime-30:$P" "$CHECK" | grep -o '"ip":"[^"]*"')
[ "$c" = "$d" ] && echo "   ok — session $S held $c" || { echo "   FAIL — session $S gave $c then $d"; fail=1; }

echo
[ "$fail" = 0 ] && echo "preflight passed" || { echo "preflight FAILED — fix the above before the drop"; exit 1; }
