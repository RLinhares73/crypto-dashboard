#!/usr/bin/env python3
"""
Appends missing daily BTC closes to data/btc-history.json.

Self-healing by design: every run looks at the last date already in the
file and fetches from (that date + 1) up to today, via CoinGecko's Demo
API. If a run is ever missed (workflow down, rate limit, etc.), the next
run just fetches a wider range and catches up -- no manual backfill step
is ever needed.

Requires the environment variable COINGECKO_API_KEY (the GitHub Actions
workflow supplies this from the repo's encrypted secret -- it is never
written to disk or committed).
"""
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "btc-history.json")
API_KEY = os.environ.get("COINGECKO_API_KEY")

if not API_KEY:
    print("ERROR: COINGECKO_API_KEY environment variable is not set.", file=sys.stderr)
    sys.exit(1)


def load_data():
    with open(DATA_PATH) as f:
        return json.load(f)


def save_data(data):
    with open(DATA_PATH, "w") as f:
        json.dump(data, f, separators=(",", ":"))
        f.write("\n")


def fetch_range(from_ts, to_ts):
    url = (
        "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart/range"
        f"?vs_currency=usd&from={from_ts}&to={to_ts}&interval=daily"
    )
    req = urllib.request.Request(url, headers={"x-cg-demo-api-key": API_KEY})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"ERROR: CoinGecko returned HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)
    return body.get("prices", [])


def main():
    data = load_data()
    if not data:
        print("ERROR: existing data file is empty -- refusing to guess a start date.", file=sys.stderr)
        sys.exit(1)

    last_date_str = data[-1][0]
    last_date = datetime.strptime(last_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)

    # Nothing to do if we're already current (today's close isn't final yet anyway).
    if last_date.date() >= (now.date() - timedelta(days=1)):
        print(f"Already up to date (last stored date: {last_date_str}). Nothing to fetch.")
        return

    from_ts = int((last_date + timedelta(days=1)).timestamp())
    to_ts = int(now.timestamp())

    prices = fetch_range(from_ts, to_ts)
    if not prices:
        print("No new price points returned.")
        return

    existing_dates = {row[0] for row in data}
    added = 0
    for ts_ms, price in prices:
        day = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        # Skip today's partial/in-progress candle and any date we already have.
        if day == now.strftime("%Y-%m-%d") or day in existing_dates:
            continue
        data.append([day, round(price, 2)])
        existing_dates.add(day)
        added += 1

    if added == 0:
        print("Fetched range but found no new complete daily closes to add.")
        return

    data.sort(key=lambda row: row[0])
    save_data(data)
    print(f"Added {added} new daily close(s). Data now runs through {data[-1][0]}.")


if __name__ == "__main__":
    main()
