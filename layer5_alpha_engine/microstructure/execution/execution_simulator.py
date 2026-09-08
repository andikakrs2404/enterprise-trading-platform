#!/usr/bin/env /usr/bin/python3.11
"""
Execution Simulator — institutional-quality fill modeling
==========================================================
Signal masuk -> berapa biaya riil yang harus dibayar?

Model:
  - Order placement: market (taker) / limit (maker)
  - Fill: taker -> walk book (slippage dari depth), garantis
          maker  -> probabilitas fill (akan dikalibrasi dari data paper/live)
  - Cost: fee + spread captured + slippage + latency penalty
  - Jangan "menganggap" fill sempurna di best price.

Digunakan di STUDY-020 (Execution Reality) dan semua net-edge evaluation.
"""
import numpy as np
from dataclasses import dataclass, field


@dataclass
class FillResult:
    filled_qty: float = 0.0
    avg_fill_price: float = 0.0
    slippage_bps: float = 0.0
    fee_bps: float = 0.0
    latency_bps: float = 0.0
    total_cost_bps: float = 0.0
    notes: str = ""


class ExecutionSimulator:
    def __init__(self, cost_model):
        self.cost = cost_model

    def market_order(self, side: str, qty: float, book,
                     fee_bps_per_side: float = None,
                     latency_bps: float = 0.0) -> FillResult:
        """Market order: walk the book to fill qty.
        book: dict with 'bids' and 'asks' (lists of [price, qty]).
        """
        levels = book["asks"] if side == "buy" else book["bids"]
        if levels is None or len(levels) == 0:
            return FillResult(notes="no book")
        remaining = qty
        notional = 0.0
        filled = 0.0
        for price, lqty in levels:
            price = float(price); lqty = float(lqty)
            take = min(remaining, lqty)
            if take <= 0:
                continue
            notional += take * price
            filled += take
            remaining -= take
            if remaining <= 0:
                break
        if filled <= 0:
            return FillResult(notes="unfilled")
        avg = notional / filled
        best = float(levels[0][0])
        mid = (float(book["asks"][0][0]) + float(book["bids"][0][0])) / 2
        slip_bps = (avg - mid) / mid * 10000 if side == "buy" else (mid - avg) / mid * 10000
        fee = self.cost.TAKER_BPS_PER_SIDE if fee_bps_per_side is None else fee_bps_per_side
        total = slip_bps + fee + latency_bps
        return FillResult(filled_qty=filled, avg_fill_price=avg,
                          slippage_bps=float(slip_bps), fee_bps=fee,
                          latency_bps=latency_bps, total_cost_bps=float(total))

    def limit_order(self, side: str, price: float, qty: float,
                    fill_prob: float = 0.5,
                    fee_bps_per_side: float = None) -> FillResult:
        """Limit order: maker fee, fill probability < 1.
        fill_prob dikalibrasi dari data (paper/live); default 0.5 konservatif.
        NOTE: jika tidak fill, opportunity cost = move yang hilang (belum dimodelkan).
        """
        fee = self.cost.MAKER_BPS_PER_SIDE if fee_bps_per_side is None else fee_bps_per_side
        if np.random.rand() > fill_prob:
            return FillResult(filled_qty=0.0, notes=f"unfilled (p={fill_prob})")
        return FillResult(filled_qty=qty, avg_fill_price=price,
                          slippage_bps=0.0, fee_bps=fee, total_cost_bps=fee,
                          notes="maker fill")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cost"))
    from pathlib import Path
    from cost_model import expected_cost_bps
    book = {"bids": [[100.0, 10.0], [99.9, 20.0]], "asks": [[100.1, 5.0], [100.2, 30.0]]}
    sim = ExecutionSimulator(expected_cost_bps)
    r = sim.market_order("buy", 10.0, book)
    print(f"market buy 10: fill={r.filled_qty} @ {r.avg_fill_price:.2f} slip={r.slippage_bps:.2f}bps cost={r.total_cost_bps:.2f}bps")
    r2 = sim.market_order("sell", 25.0, book)
    print(f"market sell 25: fill={r2.filled_qty} @ {r2.avg_fill_price:.2f} slip={r2.slippage_bps:.2f}bps cost={r2.total_cost_bps:.2f}bps")
    r3 = sim.limit_order("buy", 99.9, 5.0)
    print(f"limit buy 5: fill={r3.filled_qty} fee={r3.fee_bps}bps cost={r3.total_cost_bps}bps {r3.notes}")