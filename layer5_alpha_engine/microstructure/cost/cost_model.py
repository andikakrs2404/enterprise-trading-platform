#!/usr/bin/env /usr/bin/python3.11
"""
Cost Model — Binance USDT-M Futures (realistic, component-separated)
=====================================================================
Jangan pakai "fee = 8bps" saja. Pisahkan semua komponen biaya:

  expected_cost = fee (maker/taker) + spread + slippage + latency penalty

Semua nilai default dikunci di sini (preregistered), bukan ditentukan per-studi.

Referensi Binance USDT-M futures (VIP0, tanpa BNB discount):
  - Taker fee: 0.04% per side -> 4 bps/side -> 8 bps round-trip
  - Maker fee: 0.02% per side -> 2 bps/side -> 4 bps round-trip

Spread & slippage diukur dari data (STUDY-016B / depth walk), bukan asumsi.
Latency penalty = estimasi move yang terjadi selama signal age.
"""
import numpy as np

# ---- Fee (dikunci) ----
TAKER_BPS_PER_SIDE = 4.0
MAKER_BPS_PER_SIDE = 2.0
TAKER_RT_BPS = 8.0
MAKER_RT_BPS = 4.0

# ---- Default conservative untuk fase tanpa data depth cukup ----
DEFAULT_SPREAD_BPS = 0.1        # diukur: BTC ~0.013 bps; pakai konservatif utk non-BTC
DEFAULT_SLIPPAGE_BPS = 0.5      # fallback; seharusnya dihitung dari depth walk
DEFAULT_LATENCY_MS = 5.0        # signal age asumsi (realtime collector ~3-60ms)


def rt_fee_bps(taker: bool = True) -> float:
    """Round-trip fee in bps (entry + exit)."""
    return TAKER_RT_BPS if taker else MAKER_RT_BPS


def expected_cost_bps(taker: bool = True, spread_bps: float = None,
                      slippage_bps: float = None,
                      latency_ms: float = None,
                      latency_bps_per_ms: float = None) -> dict:
    """Breakdown of expected one-way entry+exit cost (bps of notional).

    latency_bps_per_ms: harga per ms delay (diukur nanti dari data; default 0).
    Returns breakdown dict + total.
    """
    spread = DEFAULT_SPREAD_BPS if spread_bps is None else spread_bps
    slip = DEFAULT_SLIPPAGE_BPS if slippage_bps is None else slippage_bps
    lat_bps = 0.0
    if latency_bps_per_ms is not None and latency_ms is not None:
        lat_bps = latency_ms * latency_bps_per_ms
    fee = rt_fee_bps(taker)
    total = fee + spread + slip + lat_bps
    return {
        "fee_bps": fee,
        "spread_bps": spread,
        "slippage_bps": slip,
        "latency_bps": lat_bps,
        "total_bps": total,
    }


def walk_book_slippage(bids, asks, qty: float, side: str) -> dict:
    """Walk order book levels to fill qty; return volume-weighted fill vs mid (bps).

    bids/asks: list of [price, qty] sorted (bid desc, ask asc).
    side: 'buy' -> walk asks; 'sell' -> walk bids.
    Returns fill price, slippage in bps vs mid at best level.
    """
    levels = asks if side == "buy" else bids
    if levels is None or len(levels) == 0 or qty <= 0:
        return {"fill_price": None, "slippage_bps": None, "filled": 0.0}
    remaining = qty
    fill_notional = 0.0
    fill_qty = 0.0
    for price, level_qty in levels:
        price = float(price)
        level_qty = float(level_qty)
        if level_qty <= 0:
            continue
        take = min(remaining, level_qty)
        fill_notional += take * price
        fill_qty += take
        remaining -= take
        if remaining <= 0:
            break
    if fill_qty <= 0:
        return {"fill_price": None, "slippage_bps": None, "filled": 0.0}
    fill_price = fill_notional / fill_qty
    best = float(levels[0][0])
    mid = (float(asks[0][0]) + float(bids[0][0])) / 2 if side == "buy" else \
          (float(bids[0][0]) + float(asks[0][0])) / 2
    slip_bps = (fill_price - mid) / mid * 10000 if side == "buy" else (mid - fill_price) / mid * 10000
    return {"fill_price": fill_price, "slippage_bps": float(slip_bps), "filled": float(fill_qty)}


def calibrate_spread_from_depth(depth_dir):
    """Reuse quality_report.spread_distribution to measure real spread (bps of mid)."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "collector"))
    from quality_report import spread_distribution
    from pathlib import Path
    return spread_distribution(Path(depth_dir))


if __name__ == "__main__":
    print("=== COST MODEL (preregistered defaults) ===")
    for taker in (True, False):
        c = expected_cost_bps(taker=taker)
        print(f"  {'TAKER' if taker else 'MAKER'} RT: fee={c['fee_bps']} + spread={c['spread_bps']} "
              f"+ slip={c['slippage_bps']} + lat={c['latency_bps']} = {c['total_bps']:.2f} bps")