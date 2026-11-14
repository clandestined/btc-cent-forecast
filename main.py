#!/usr/bin/env python3
"""btc-cent-forecast-01: persistence forecast of BTC/USD 4 hours ahead,
with a guard against one-minute flash prints in the checkpoint close.

Model (Python 3.13 standard library only, deterministic, no network):
  The forecast is the checkpoint close itself (persistence), unless that
  close sits more than 1% away from the median of the last 10 closes, in
  which case the 10-minute median is used instead. The price comes from a
  single Orca pool (CBBTC/USDC), and one unusually large trade can move
  that pool's print for a moment, so a one-minute flash print is not the
  market. The 1% line is deliberate: a smaller line fires on ordinary
  fast moves, where the median is just a stale price and the last close
  is right.

Why nothing else: at a 4-hour horizon Bitcoin is, to every test I could
run, a random walk around its current price, and every tilt I tried
failed an honest check. Momentum, trend extrapolation, mean reversion
toward the 4 h / 6 h / 24 h / 72 h mean, blends of the two, EWMA anchors
and a drift fitted to the trailing 72 h were all swept over the practice
cases, a 17-checkpoint hourly grid over the practice window, a 5,271
minute-by-minute checkpoint scan of the whole practice window, and a
257-checkpoint hourly grid of Coinbase BTC-USD closes (Nov 4-14). The
tilts that looked better on one grid lost on another: the best-looking,
mean reversion toward the 6 h mean, won the whole of its edge in the
Nov 10 afternoon bounce (it lost the morning, +1,762 cents, and won the
afternoon, -3,278), and was flat on the first half of the Coinbase
window (+14 cents). A tilt that only wins in one regime is regime-fitting,
not forecasting, so none shipped. Persistence is the forecast; the only
adjustment is the flash-print guard, which is the one place the checkpoint
close itself can be wrong.

Calibration of the guard (the evidence for the 1% line):
  - On the 5,271-checkpoint pool scan it fires 4 times, all four minutes
    of the 2026-11-08 21:56 flash crash (-1.65% in one minute, recovered
    at once): mean paired gain vs persistence -78.8 cents per checkpoint.
  - On a 19,672-checkpoint Coinbase scan it fires 6 times for -14.3
    cents per checkpoint; of the 6 extreme minutes there, 4 reverted
    toward the median within 10 minutes, i.e. they were flash prints,
    not genuine moves.
  - The 0.3% line the first draft used fires 95 times on the pool scan
    and is a small net loser (+59.7 cents per checkpoint; +149.3 on
    Coinbase): most 0.3% deviations are genuine fast moves, where the
    median is stale. So the line is 1%, not 0.3%.
  - On the practice cases the guard never fires (largest deviation
    0.17%), so the practice score equals the persistence baseline:
    44,521.576667 cents over all six cases (p05's target, 73,864.44322,
    recovered from the baseline's published practice loss of
    44,521.576667 cents and cross-checked against the Coinbase close
    at that minute, 73,837.72).

Usage: python3 main.py -- reads every *.in in $MAKEFUN_INPUT_DIR (else
/input) and writes <id>.out to $MAKEFUN_OUTPUT_DIR (else /output), one
JSON object {"forecasts": [{"case": <id>, "price": <guess>}]} per case.
"""

import json
import math
import os
import statistics
from pathlib import Path

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

MIN_PRICE = 0.00001
MAX_PRICE = 9_999_999.99999
SPIKE_WINDOW = 10          # closes used for the median anchor check
SPIKE_THRESHOLD = 0.01     # 1%: last close vs 10-minute median
FALLBACK_PRICE = 1.0       # only if a case holds no usable price at all


def price5(x):
    """Keep x on the grid's 5 decimals and inside the scorer's (0, 10M).

    Rounds half away from zero, matching the kit starter's Math.round:
    the median of an even window can land exactly on a half unit of the
    grid, and Python's round() would banker's-round it instead.
    """
    clamped = min(MAX_PRICE, max(MIN_PRICE, x))
    return math.floor(clamped * 100000 + 0.5) / 100000


def clean_prices(raw):
    """Finite numbers from a case's prices, in order; skips junk entries."""
    prices = []
    if isinstance(raw, list):
        for value in raw:
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)) and math.isfinite(value):
                prices.append(float(value))
    return prices


def forecast(prices):
    """One forecast from a case's closes (last one is the checkpoint close)."""
    if not prices:
        return FALLBACK_PRICE
    last = prices[-1]
    window = prices[-SPIKE_WINDOW:]
    median = statistics.median(window)
    anchor = median if abs(last - median) > SPIKE_THRESHOLD * abs(last) else last
    return price5(anchor)


def forecast_case(case):
    """Forecast for one parsed case object; never raises on bad input."""
    try:
        markets = case.get("markets") if isinstance(case, dict) else None
        if isinstance(markets, list) and markets:
            market = markets[0]
            raw = market.get("prices") if isinstance(market, dict) else None
            prices = clean_prices(raw)
            if prices:
                return forecast(prices)
    except (AttributeError, TypeError, ValueError):
        pass
    return FALLBACK_PRICE


def main():
    in_dir = Path(INPUT_DIR)
    out_dir = Path(OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not in_dir.is_dir():
        return
    for path in sorted(in_dir.glob("*.in")):
        case_id = path.name[: -len(".in")]
        try:
            with open(path, encoding="utf-8") as fh:
                case = json.load(fh)
        except (OSError, ValueError):
            case = None
        price = forecast_case(case)
        payload = {"forecasts": [{"case": case_id, "price": price}]}
        with open(out_dir / f"{case_id}.out", "w", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")


if __name__ == "__main__":
    main()
