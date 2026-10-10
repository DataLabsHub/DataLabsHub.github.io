"""Fetch CNY exchange rates and write them to a JSON file read by the handbook pages.

Keeps the existing file when every source fails or returns implausible values,
so a bad upstream day never breaks the published prices.
"""
import datetime
import json
import sys
import urllib.request

CURRENCIES = ["TWD", "USD", "JPY", "KRW", "EUR", "BRL", "RUB"]
MAX_DAILY_SWING = 0.3
MIRROR = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{tag}/v1/currencies/cny.json"


def sources():
    today = datetime.datetime.now(datetime.timezone.utc).date()
    for offset in (0, 1):
        yield MIRROR.format(tag=(today - datetime.timedelta(days=offset)).isoformat())
    yield "https://latest.currency-api.pages.dev/v1/currencies/cny.json"
    yield MIRROR.format(tag="latest")


def fetch(url):
    with urllib.request.urlopen(url, timeout=20) as resp:
        data = json.load(resp)
    return data["date"], {c: float(data["cny"][c.lower()]) for c in CURRENCIES}


def plausible(rates, previous):
    for c in CURRENCIES:
        value = rates.get(c)
        if not value or value <= 0:
            return False
        old = previous.get(c)
        if old and abs(value / old - 1) > MAX_DAILY_SWING:
            return False
    return True


def main(path):
    try:
        with open(path, encoding="utf-8") as f:
            previous = json.load(f).get("rates", {})
    except (OSError, ValueError):
        previous = {}

    candidates = []
    for url in sources():
        try:
            date, rates = fetch(url)
        except Exception as exc:
            print(f"skip {url}: {exc}")
            continue
        if not plausible(rates, previous):
            print(f"skip {url}: implausible values {rates}")
            continue
        print(f"ok {url}: {date}")
        candidates.append((date, url, rates))

    if not candidates:
        print("all sources failed, keeping previous rates")
        return

    date, url, rates = max(candidates, key=lambda c: c[0])
    payload = {"base": "CNY", "date": date, "rates": {c: round(rates[c], 6) for c in CURRENCIES}}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"updated from {url}: {payload}")


if __name__ == "__main__":
    main(sys.argv[1])
