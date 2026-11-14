# btc-cent-forecast-01

Forecast Bitcoin's USD price 4 hours ahead from the last 72 hours of
1-minute closes, for the make.fun bounty `btc-cent-forecast-01`.

## Entry point

`main.py` (Python 3.13, standard library only, no network, deterministic).
It reads every `*.in` in `$MAKEFUN_INPUT_DIR` (else `/input`) and writes
`<id>.out` to `$MAKEFUN_OUTPUT_DIR` (else `/output`):

```json
{"forecasts": [{"case": "p00", "price": 74764.91526}]}
```

Run locally:

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

## Approach

Persistence, with a guard against one-minute flash prints. The forecast
is the checkpoint close itself, unless that close sits more than 1% away
from the median of the last 10 closes, in which case the 10-minute median
is used instead: the price comes from a single Orca pool, and one large
trade can move its print for a moment, so a one-minute flash print is not
the market.

Why no tilt: momentum, trend extrapolation, mean reversion toward the
4 h / 6 h / 24 h / 72 h mean, blends, EWMA anchors and a trailing-72 h
drift were all swept over the practice cases, a 17-checkpoint hourly
grid, a 5,271 minute-by-minute checkpoint scan of the practice window,
and a 257-checkpoint Coinbase grid (Nov 4-14). Every tilted variant
failed an honest check: the best-looking one won its whole edge in a
single afternoon bounce and lost the morning and the first half of the
Coinbase window. A tilt that only wins in one regime is regime-fitting,
so none shipped. The 1% guard is the only adjustment, and the 0.3% line
an earlier draft used was dropped after the scans showed it is a small
net loser (it fires on genuine fast moves, where the median is stale).

## Validation (practice cases)

- Practice p00-p05: MAE **44,521.576667 cents**, exactly the persistence
  baseline — the guard never fires on these cases (largest deviation
  from the 10-minute median is 0.17%). The p05 target (73,864.44322)
  was recovered from the baseline's published practice loss and
  cross-checked against the Coinbase close at that minute (73,837.72).
- Wider backtest, 5,271 minute-by-minute checkpoints over the practice
  window: **-78.8 cents per checkpoint vs persistence**, the whole gain
  from the 2026-11-08 21:56 flash crash (-1.65% in one minute, recovered
  at once), where raw persistence erred by 145,332 cents at that minute
  and this model by 12,445 cents.
- A 19,672-checkpoint Coinbase scan agrees: -14.3 cents per checkpoint,
  and 4 of its 6 extreme minutes reverted toward the median within
  10 minutes, i.e. they were flash prints, not genuine moves.
- Determinism: two runs on all six practice cases produce byte-identical
  outputs. Runtime: ~0.03 s per case (limit 8 s).
