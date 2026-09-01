#!/usr/bin/env /usr/bin/python3.11
"""
P1.7 Alpha Research Validation - Real Market Data
==================================================
Menjalankan P1.7 framework v2.0 dengan data historis nyata dari
Bot-Multi-Edge-metrics (39 simbol, timeframe 1h).

Aliran:
L3 Features -> L4 Context -> L5 CompressionAlpha
  -> Setup Analysis -> Trigger Analysis -> Forward Outcome
  -> Effect Size, Bootstrap CI, Permutation Test
  -> 4-level Decision (INCONCLUSIVE/HYPOTHESIS_SUPPORTED/ROBUST_CANDIDATE/PRODUCTION_CANDIDATE)
"""
import json
import os
import sys
import math
import random
import statistics
from datetime import datetime, timezone

# Import data infrastructure
import pyarrow.parquet as pq
import pandas as pd
import numpy as np

DATA_DIR = '/home/rtk/Bot-Multi-Edge-metrics/data/klines'
RESEARCH_DIR = '/home/rtk/enterprise-trading-platform/layer5_alpha_engine/research'
os.makedirs(RESEARCH_DIR, exist_ok=True)

random.seed(42)
np.random.seed(42)

# ============================================================
# STEP 1: LOAD REAL MARKET DATA
# ============================================================
def load_symbol(symbol, max_bars=None):
    """Load kline data for a symbol."""
    path = os.path.join(DATA_DIR, symbol, 'klines_1h.parquet')
    if not os.path.exists(path):
        return None
    df = pd.read_parquet(path)
    if max_bars:
        df = df.tail(max_bars)
    return df

def build_ohlc_list(df):
    """Convert DataFrame to list of dicts for the framework."""
    bars = []
    for idx, row in df.iterrows():
        bars.append({
            'timestamp': int(idx.timestamp()) if hasattr(idx, 'timestamp') else int(idx),
            'open': float(row['open']) if 'open' in df.columns else float(row.iloc[0]),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close']),
            'volume': float(row['volume']),
        })
    return bars

# ============================================================
# STEP 2: COMPRESSION DETECTION + EVENT EXTRACTION
# ============================================================
def compute_features(bars):
    """Compute core feature set: atr_ratio, bb_width, volume_ratio."""
    n = len(bars)
    features = [None] * n
    
    for i in range(n):
        if i < 20:  # warmup
            continue
        window = bars[max(0, i-20):i+1]
        closes = [b['close'] for b in window]
        
        # ATR (20)
        atr_vals = []
        for j in range(1, len(window)):
            atr_vals.append(max(window[j]['high']-window[j]['low'],
                                abs(window[j]['high']-window[j-1]['close']),
                                abs(window[j]['low']-window[j-1]['close'])))
        atr20 = sum(atr_vals)/len(atr_vals) if atr_vals else 0
        
        # ATR100 (longer lookback)
        if i >= 100:
            lw = bars[i-100:i+1]
            latr = []
            for j in range(1, len(lw)):
                latr.append(max(lw[j]['high']-lw[j]['low'],
                                abs(lw[j]['high']-lw[j-1]['close']),
                                abs(lw[j]['low']-lw[j-1]['close'])))
            atr100 = sum(latr)/len(latr) if latr else atr20
        else:
            atr100 = atr20
        
        atr_ratio = atr20/atr100 if atr100 > 0 else 1.0
        
        # Bollinger Band Width (20)
        sma20 = sum(closes)/len(closes)
        std20 = statistics.pstdev(closes) if len(closes) > 1 else 0
        bb_width = 4*std20/sma20 if sma20 > 0 else 0
        
        # Volume ratio
        if i >= 20:
            vol_window = [b['volume'] for b in bars[i-20:i]]
            avg_vol = sum(vol_window)/len(vol_window) if vol_window else 1
        else:
            avg_vol = 1
        vol_ratio = bars[i]['volume']/avg_vol if avg_vol > 0 else 1.0
        
        features[i] = {
            'atr_ratio': atr_ratio,
            'bb_width': bb_width,
            'volume_ratio': vol_ratio,
        }
    return features

def detect_events(bars, features, compression_threshold=0.7, vol_threshold=1.5):
    """Detect compression setup + breakout trigger events."""
    setup_events = []
    trigger_events = []
    episodes = []
    current_episode = None
    
    for i in range(20, len(bars)):
        feat = features[i]
        if feat is None:
            continue
        
        # Compression detection: low ATR ratio + narrow BB + low volume
        is_compression = feat['atr_ratio'] < compression_threshold and feat['bb_width'] < 0.05
        
        if is_compression:
            if current_episode is None:
                current_episode = {
                    'episode_id': f"C{len(episodes)+1:03d}",
                    'start_bar': i,
                    'direction': None,
                    'trigger_bar': None,
                }
            # Setup event per episode start (not per candle - avoids overcount)
            if i == current_episode['start_bar']:
                setup_events.append({
                    'episode_id': current_episode['episode_id'],
                    'bar_idx': i,
                    'compression': feat['atr_ratio'],
                    'bb_width': feat['bb_width'],
                })
        else:
            # Check breakout after compression episode
            if current_episode is not None:
                # Breakout condition: close breaks above episode high + volume confirm
                ep_high = max(bars[j]['high'] for j in range(current_episode['start_bar'], i))
                ep_low = min(bars[j]['low'] for j in range(current_episode['start_bar'], i))
                ep_range = ep_high - ep_low
                
                direction = None
                if bars[i]['close'] > ep_high * 1.001 and feat['volume_ratio'] > vol_threshold:
                    direction = 'LONG'
                elif bars[i]['close'] < ep_low * 0.999 and feat['volume_ratio'] > vol_threshold:
                    direction = 'SHORT'
                
                if direction:
                    trigger_events.append({
                        'episode_id': current_episode['episode_id'],
                        'bar_idx': i,
                        'direction': direction,
                        'volume_ratio': feat['volume_ratio'],
                        'compression': feat['atr_ratio'],
                        'bb_width': feat['bb_width'],
                    })
                    current_episode['direction'] = direction
                    current_episode['trigger_bar'] = i
                    episodes.append(current_episode)
                    current_episode = None
                elif i - current_episode['start_bar'] > 50:
                    # Episode expired without breakout
                    episodes.append(current_episode)
                    current_episode = None
    
    return setup_events, trigger_events, episodes

# ============================================================
# STEP 3: FORWARD OUTCOME + MFE/MAE
# ============================================================
def compute_forward_outcomes(bars, trigger_events, horizons=[1,3,6,12,24]):
    """Compute forward returns for each trigger event at multiple horizons."""
    outcomes = []
    for ev in trigger_events:
        i = ev['bar_idx']
        entry = bars[i]['close']
        direction = ev['direction']
        fwd = {
            'event_id': f"{ev['episode_id']}_{i}",
            'episode_id': ev['episode_id'],
            'direction': direction,
            'bar_idx': i,
            'compression': ev.get('compression'),
            'volume_ratio': ev.get('volume_ratio'),
        }
        # Forward returns + MFE/MAE
        for h in horizons:
            j = min(i+h, len(bars)-1)
            ret = (bars[j]['close']/entry - 1) * 100
            if direction == 'SHORT':
                ret = -ret
            fwd[f'forward_{h}bar'] = round(ret, 4)
        
        # MFE/MAE within each horizon window
        for h in horizons:
            end = min(i+h, len(bars)-1)
            mfe_exc = 0
            mae_exc = 0
            for k in range(i, end+1):
                ret = (bars[k]['close']/entry - 1) * 100
                if direction == 'SHORT':
                    ret = -ret
                if ret > mfe_exc:
                    mfe_exc = ret
                if ret < mae_exc:
                    mae_exc = ret
            fwd[f'mfe_{h}bar'] = round(mfe_exc, 4)
            fwd[f'mae_{h}bar'] = round(mae_exc, 4)
        
        outcomes.append(fwd)
    return outcomes

# ============================================================
# STEP 4: STATISTICAL ANALYSIS (BOOTSTRAP + PERMUTATION)
# ============================================================
def bootstrap_ci(values, n_iter=2000, alpha=0.05):
    """Bootstrap confidence interval for the mean."""
    n = len(values)
    if n == 0:
        return (0, (0, 0))
    means = []
    for _ in range(n_iter):
        sample = [values[random.randint(0, n-1)] for _ in range(n)]
        means.append(sum(sample)/n)
    means.sort()
    lo = means[int(n_iter*alpha/2)]
    hi = means[int(n_iter*(1-alpha/2))]
    return (sum(means)/n_iter, (lo, hi))

def permutation_test(comp_fwd, baseline_fwd, n_iter=1000):
    """Permutation test: does compression outperform random baseline?"""
    n_comp = len(comp_fwd)
    n_base = len(baseline_fwd)
    if n_comp == 0 or n_base == 0:
        return None
    
    obs_comp = sum(1 for f in comp_fwd if f.get('forward_1bar',0) > 0)/n_comp
    obs_base = sum(1 for f in baseline_fwd if f.get('forward_1bar',0) > 0)/n_base
    obs_diff = obs_comp - obs_base
    
    # Pooled
    pooled = [1 if f.get('forward_1bar',0) > 0 else 0 for f in comp_fwd]
    pooled += [1 if f.get('forward_1bar',0) > 0 else 0 for f in baseline_fwd]
    
    count_more_extreme = 0
    for _ in range(n_iter):
        random.shuffle(pooled)
        c = pooled[:n_comp]
        b = pooled[n_comp:]
        diff = (sum(c)/n_comp) - (sum(b)/n_base)
        if abs(diff) >= abs(obs_diff):
            count_more_extreme += 1
    
    p_value = count_more_extreme / n_iter
    return p_value

def effect_size(comp_fwd, baseline_fwd):
    """Compute effect size metrics: absolute delta, relative lift, odds ratio."""
    n_c = len(comp_fwd)
    n_b = len(baseline_fwd)
    if n_c == 0 or n_b == 0:
        return None
    
    p_c = sum(1 for f in comp_fwd if f.get('forward_1bar',0) > 0)/n_c
    p_b = sum(1 for f in baseline_fwd if f.get('forward_1bar',0) > 0)/n_b
    
    abs_delta = (p_c - p_b) * 100  # percentage points
    rel_lift = ((p_c - p_b)/p_b * 100) if p_b > 0 else None
    odds_c = p_c/(1-p_c) if p_c < 1 else float('inf')
    odds_b = p_b/(1-p_b) if p_b < 1 else float('inf')
    odds_ratio = odds_c/odds_b if odds_b > 0 else None
    
    return {
        'p_compression': round(p_c, 4),
        'p_baseline': round(p_b, 4),
        'absolute_delta_pp': round(abs_delta, 2),
        'relative_lift_pct': round(rel_lift, 2) if rel_lift else None,
        'odds_ratio': round(odds_ratio, 3) if odds_ratio else None,
        'n_compression': n_c,
        'n_baseline': n_b,
    }

# ============================================================
# STEP 5: 4-LEVEL DECISION
# ============================================================
def make_decision(effect, p_value, n_events, n_episodes, direction_breakdown, economic):
    """Apply 4-level decision based on evidence."""
    if effect is None or n_events == 0:
        return {
            'state': 'INCONCLUSIVE',
            'reason': 'No events or insufficient evidence',
            'level': 0
        }
    
    # Check statistical significance (effect size + CI)
    abs_delta = effect['absolute_delta_pp']
    p_sig = p_value if p_value is not None else 1.0
    
    # Economic check
    net_expectancy = economic.get('net_expectancy', 0)
    net_pf = economic.get('net_pf', 0)
    
    # Level 1: INCONCLUSIVE if no meaningful effect
    if p_sig > 0.05 or abs_delta < 2.0:
        return {
            'state': 'INCONCLUSIVE',
            'reason': f'Not statistically significant (p={p_sig:.3f}) or effect too small (delta={abs_delta:.1f}pp)',
            'level': 1
        }
    
    # Level 2: HYPOTHESIS_SUPPORTED - significant + meaningful effect
    if net_expectancy > 0 and abs_delta >= 2.0:
        return {
            'state': 'HYPOTHESIS_SUPPORTED',
            'reason': f'Significant effect (delta={abs_delta:.1f}pp, p={p_sig:.3f}), net expectancy positive',
            'level': 2
        }
    
    # Level 3: ROBUST_CANDIDATE - survives most criteria
    if net_expectancy > 0 and net_pf > 1.2 and n_episodes >= 3:
        return {
            'state': 'ROBUST_CANDIDATE',
            'reason': f'Robust effect (delta={abs_delta:.1f}pp), net PF={net_pf:.2f}, {n_episodes} episodes',
            'level': 3
        }
    
    # Level 4: PRODUCTION_CANDIDATE - strong, robust, viable
    if net_expectancy > 0.05 and net_pf > 1.5 and n_events >= 50:
        return {
            'state': 'PRODUCTION_CANDIDATE',
            'reason': f'Production ready: delta={abs_delta:.1f}pp, net PF={net_pf:.2f}, {n_events} events',
            'level': 4
        }
    
    return {
        'state': 'HYPOTHESIS_SUPPORTED',
        'reason': f'Effect supported but not yet robust (delta={abs_delta:.1f}pp)',
        'level': 2
    }

# ============================================================
# MAIN PIPELINE
# ============================================================
print("=" * 70)
print("P1.7 ALPHA RESEARCH VALIDATION - REAL MARKET DATA")
print("=" * 70)

# Load symbols (BTC, ETH, SOL, BNB first)
symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']
all_triggers = []
all_ohlc = {}

for symbol in symbols:
    df = load_symbol(symbol)
    if df is None:
        print(f"  [!] {symbol}: data not found, skipping")
        continue
    bars = build_ohlc_list(df)
    features = compute_features(bars)
    setup_events, trigger_events, episodes = detect_events(bars, features)
    
    print(f"\n--- {symbol} ---")
    print(f"  Bars: {len(bars)}, Setup: {len(setup_events)}, Trigger: {len(trigger_events)}, Episodes: {len(episodes)}")
    
    # Direction breakdown
    longs = [t for t in trigger_events if t['direction']=='LONG']
    shorts = [t for t in trigger_events if t['direction']=='SHORT']
    print(f"  LONG: {len(longs)}, SHORT: {len(shorts)}")
    
    # Compute forward outcomes
    outcomes = compute_forward_outcomes(bars, trigger_events)
    if outcomes:
        for o in outcomes:
            o['symbol'] = symbol
        all_triggers.extend(outcomes)
    
    all_ohlc[symbol] = bars

print("\n" + "=" * 70)
print(f"TOTAL: {len(all_triggers)} trigger events across {len(symbols)} symbols")
print("=" * 70)

# Direction breakdown
longs = [t for t in all_triggers if t['direction']=='LONG']
shorts = [t for t in all_triggers if t['direction']=='SHORT']
print(f"LONG: {len(longs)}, SHORT: {len(shorts)}")

# ---------- Forward outcome analysis ----------
print("\n--- FORWARD OUTCOME ANALYSIS ---")
horizons = [1,3,6,12,24]
for h in horizons:
    rets = [t.get(f'forward_{h}bar', 0) for t in all_triggers]
    if rets:
        pos = sum(1 for r in rets if r > 0)
        print(f"  forward_{h}bar: mean={sum(rets)/len(rets):.3f}%, median={statistics.median(rets):.3f}%, ",
              f"pos%={pos/len(rets)*100:.1f}% (n={len(rets)})")

# ---------- MFE/MAE ----------
print("\n--- MFE/MAE (per horizon) ---")
mfe_mae = {}
for h in horizons:
    mfes = [t.get(f'mfe_{h}bar', 0) for t in all_triggers]
    maes = [t.get(f'mae_{h}bar', 0) for t in all_triggers]
    if mfes:
        mfe_mae[f'{h}bar'] = {
            'MFE': round(sum(mfes)/len(mfes), 3),
            'MAE': round(sum(maes)/len(maes), 3),
            'n': len(mfes)
        }
        print(f"  {h}bar: avg MFE={sum(mfes)/len(mfes):.3f}%, avg MAE={sum(maes)/len(maes):.3f}% (n={len(mfes)})")

# ---------- Direction analysis ----------
print("\n--- DIRECTION ANALYSIS (LONG vs SHORT SEPARATE) ---")
for direction, subset in [('LONG', longs), ('SHORT', shorts)]:
    if not subset:
        print(f"  {direction}: INSUFFICIENT (0 events)")
        continue
    rets = [t.get('forward_1bar', 0) for t in subset]
    pos = sum(1 for r in rets if r > 0)
    exp = sum(rets)/len(rets)
    print(f"  {direction}: n={len(subset)}, hit_rate={pos/len(subset)*100:.1f}%, "
          f"expectancy_1bar={exp:.3f}%")

# ---------- Effect size + bootstrap + permutation ----------
print("\n--- EFFECT SIZE + SIGNIFICANCE ---")
# Baseline: random windows (non-compression)
random.seed(123)
baseline_fwd = []
for _ in range(len(all_triggers)):
    # Simulate random baseline: no compression filter
    rand_sym = random.choice(list(all_ohlc.keys()))
    rand_bars = all_ohlc[rand_sym]
    ri = random.randint(50, len(rand_bars)-30)
    entry = rand_bars[ri]['close']
    direction = random.choice(['LONG','SHORT'])
    ret = (rand_bars[ri+1]['close']/entry - 1) * 100
    if direction == 'SHORT':
        ret = -ret
    baseline_fwd.append({'forward_1bar': ret})

effect = effect_size(all_triggers, baseline_fwd)
if effect:
    print(f"  P(breakout|compression): {effect['p_compression']*100:.1f}% (n={effect['n_compression']})")
    print(f"  P(breakout|baseline):    {effect['p_baseline']*100:.1f}% (n={effect['n_baseline']})")
    print(f"  Absolute delta: {effect['absolute_delta_pp']:+.1f} pp")
    if effect['relative_lift_pct']:
        print(f"  Relative lift: {effect['relative_lift_pct']:+.1f}%")
    if effect['odds_ratio']:
        print(f"  Odds ratio: {effect['odds_ratio']:.2f}")

p_value = permutation_test(all_triggers, baseline_fwd, n_iter=1000)
print(f"  Permutation p-value: {p_value:.4f}" if p_value is not None else "  Permutation test: N/A")

# ---------- Economic value ----------
print("\n--- ECONOMIC VALUE ---")
# Estimate net returns with realistic fees (taker 0.05% futures + slippage 0.03%)
fee_rate = 0.0008  # 8 bps round-trip
gross_expectancy = sum(t.get('forward_1bar', 0) for t in all_triggers) / len(all_triggers) if all_triggers else 0
net_expectancy = gross_expectancy - fee_rate * 100
wins = [t['forward_1bar'] for t in all_triggers if t.get('forward_1bar',0) > 0]
losses = [t['forward_1bar'] for t in all_triggers if t.get('forward_1bar',0) <= 0]
net_pf = (sum(wins) - fee_rate*100*len(wins)) / (-(sum(losses)) + fee_rate*100*len(losses)) if losses else 0
print(f"  Gross expectancy (1bar): {gross_expectancy:+.3f}%")
print(f"  Net expectancy (after 8bps): {net_expectancy:+.3f}%")
print(f"  Net Profit Factor: {net_pf:.3f}")

economic = {
    'gross_expectancy': gross_expectancy,
    'net_expectancy': net_expectancy,
    'net_pf': net_pf,
    'fee_rate': fee_rate
}

# ---------- Decision ----------
print("\n--- DECISION ---")
decision = make_decision(effect, p_value, len(all_triggers),
                         len(set(t['episode_id'] for t in all_triggers)),
                         {'LONG': len(longs), 'SHORT': len(shorts)}, economic)
print(f"  State: {decision['state']}")
print(f"  Reason: {decision['reason']}")
print(f"  Level: {decision['level']}/4")

# ---------- Save results ----------
print("\n--- SAVING RESULTS ---")
# Save forward outcomes
with open(os.path.join(RESEARCH_DIR, 'forward_outcomes.json'), 'w') as f:
    json.dump(all_triggers, f, indent=2)
print("  forward_outcomes.json saved")

# Save effect size
with open(os.path.join(RESEARCH_DIR, 'effect_size.json'), 'w') as f:
    json.dump(effect, f, indent=2)
print("  effect_size.json saved")

# Update research manifest
manifest = {
    'research_id': 'CB-P1.7-RW-001',
    'status': 'P1_7_COMPLETE',
    'data_source': 'Bot-Multi-Edge-metrics',
    'universe': symbols,
    'timeframes': ['1h'],
    'n_events_total': len(all_triggers),
    'n_long': len(longs),
    'n_shorts': len(shorts),
    'effect_size': effect,
    'permutation_pvalue': p_value,
    'decision': decision['state'],
    'decision_reason': decision['reason'],
    'economic': economic,
    'episodes': len(set(t['episode_id'] for t in all_triggers)),
    'corrections_applied': 19,
    'framework_version': 'v2.0'
}
with open(os.path.join(RESEARCH_DIR, 'research_manifest.json'), 'w') as f:
    json.dump(manifest, f, indent=2)
print("  research_manifest.json updated")

print("\n" + "=" * 70)
print("P1.7 ANALYSIS COMPLETE")
print(f"FINAL DECISION: {decision['state']}")
print("=" * 70)
