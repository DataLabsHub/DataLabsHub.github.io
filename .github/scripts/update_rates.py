"""Fetch CNY exchange rates and write them to a JSON file used by the handbook pages.

Keeps the existing file when every source fails or returns implausible values,
so a bad upstream day never breaks the published prices.
"""
import json
import sys
import urllib.request

CURRENCIES = ["TWD", "USD", "JPY", "KRW", "EUR", "BRL", "RUB"]
MAX_DAILY_SWING = 0.3


def from_currency_api(url):
    data = json.load(urllib.request.urlopen(url, timeout=20))
    return data["date"], {c: float(data["cny"][c.lower()]) for c in CURRENCIES}


def from_er_api(url):
    data = json.load(urllib.request.urlopen(url, timeout=20))
    if data.get("result") != "success":
        raise ValueError("upstream error")
    date = data["time_last_update_utc"]
    months = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
    _, day, mon, year = date.split()[:4]
    return f"{year}-{months[mon]:02d}-{int(day):02d}", {c: float(data["rates"][c]) for c in CURRENCIES}


SOURCES = [
    (from_currency_api, "https://latest.currency-api.pages.dev/v1/currencies/cny.json"),
    (from_currency_api, "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/cny.json"),
    (from_er_api, "https://open.er-api.com/v6/latest/CNY"),
]


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

    for fetch, url in SOURCES:
        try:
            date, rates = fetch(url)
        except Exception as exc:
            print(f"skip {url}: {exc}")
            continue
        if not plausible(rates, previous):
            print(f"skip {url}: implausible values {rates}")
            continue
        payload = {"base": "CNY", "date": date, "rates": {c: round(rates[c], 6) for c in CURRENCIES}}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"updated from {url}: {payload}")
        return

    print("all sources failed, keeping previous rates")


if __name__ == "__main__":
    main(sys.argv[1])
