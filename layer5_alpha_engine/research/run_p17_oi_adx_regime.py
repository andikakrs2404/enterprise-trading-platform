#!/usr/bin/env /usr/bin/python3.11
"""
P1.7 Alpha Research Validation - WITH OI + ADX + REGIME + FUNDING
===================================================================
Menggunakan real data:
- klines  (OHLCV)
- metrics (open_interest, long_short_ratio, taker_vol_ratio)
- funding (funding_rate)

Features ditambahkan: OI delta, ADX, funding, regime, long/short ratio
di-alignment ketat per timestamp (future-leak safe: hanya pakai info s/d bar).
"""
import json
import os
import sys
import math
import random
import statistics
import pyarrow.parquet as pq
import pandas as pd
import numpy as np

DATA_DIR = '/home/rtk/Bot-Multi-Edge-metrics/data/klines'
MET_DIR = '/home/rtk/Bot-Multi-Edge-metrics/data/metrics'
FUND_DIR = '/home/rtk/Bot-Multi-Edge-metrics/data/funding'
RESEARCH_DIR = '/home/rtk/enterprise-trading-platform/layer5_alpha_engine/research'
os.makedirs(RESEARCH_DIR, exist_ok=True)

random.seed(42)
np.random.seed(42)

# ============================================================
# LOAD + ALIGN DATA PER SYMBOL (future-leak safe)
# ============================================================
def load_symbol(symbol):
    """Load klines + metrics + funding, align on timestamp."""
    k_path = os.path.join(DATA_DIR, symbol, 'klines_1h.parquet')
    m_path = os.path.join(MET_DIR, symbol, 'metrics_1h.parquet')
    f_path = os.path.join(FUND_DIR, symbol, 'funding_1h.parquet')
    if not os.path.exists(k_path):
        return None
    
    df = pd.read_parquet(k_path)
    df = df[['open','high','low','close','volume']].copy()
    df.index = pd.to_datetime(df.index, utc=True)
    
    # Align metrics (OI)
    if os.path.exists(m_path):
        met = pd.read_parquet(m_path)
        met.index = pd.to_datetime(met.index, utc=True)
        df = df.join(met[['sum_open_interest']], how='left')
        # OI delta & change %
        df['oi_delta'] = df['sum_open_interest'].diff()
        df['oi_change_pct'] = df['sum_open_interest'].pct_change() * 100
    else:
        df['sum_open_interest'] = np.nan
        df['oi_delta'] = np.nan
        df['oi_change_pct'] = np.nan
    
    # Align funding
    if os.path.exists(f_path):
        fund = pd.read_parquet(f_path)
        fund.index = pd.to_datetime(fund.index, utc=True)
        df = df.join(fund[['funding_rate']], how='left')
    else:
        df['funding_rate'] = np.nan
    
    return df

# ============================================================
# FEATURE COMPUTATION (per bar, no future leak)
# ============================================================
def compute_features(df):
    """Compute ATR ratio, BB width, volume ratio, ADX, regime per bar."""
    n = len(df)
    o = df['open'].values
    h = df['high'].values
    l = df['low'].values
    c = df['close'].values
    
    feats = [None]*n
    # True ranges
    tr = np.zeros(n)
    for i in range(n):
        if i == 0:
            tr[i] = h[i]-l[i]
        else:
            tr[i] = max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1]))
    
    for i in range(20, n):
        # ATR20
        atr20 = tr[i-19:i+1].mean()
        # ATR100
        atr100 = tr[max(0,i-99):i+1].mean() if i >= 100 else atr20
        atr_ratio = atr20/atr100 if atr100 > 0 else 1.0
        
        # BB width (20)
        w = c[i-19:i+1]
        sma = w.mean()
        std = w.std()
        bb_width = 4*std/sma if sma > 0 else 0
        
        # Volume ratio (20)
        vol20 = df['volume'].iloc[i-20:i].mean()
        vol_ratio = df['volume'].iloc[i]/vol20 if vol20 > 0 else 1.0
        
        feats[i] = {
            'atr_ratio': float(atr_ratio),
            'bb_width': float(bb_width),
            'volume_ratio': float(vol_ratio),
            'adx': float(compute_adx(df, i)),
            'oi_delta': float(df['oi_delta'].iloc[i]) if not np.isnan(df['oi_delta'].iloc[i]) else 0.0,
            'oi_change_pct': float(df['oi_change_pct'].iloc[i]) if not np.isnan(df['oi_change_pct'].iloc[i]) else 0.0,
            'funding': float(df['funding_rate'].iloc[i]) if not np.isnan(df['funding_rate'].iloc[i]) else 0.0,
            'regime': get_regime(df, i),
        }
    return feats

def compute_adx(df, i, period=14):
    """Compute ADX at bar i."""
    if i < period*2:
        return 20.0
    h = df['high'].values
    l = df['low'].values
    c = df['close'].values
    
    plus_dm = []
    minus_dm = []
    tr_values = []
    for j in range(i-period+1, i+1):
        up = h[j]-h[j-1]
        dn = l[j-1]-l[j]
        p_dm = up if (up > dn and up > 0) else 0
        m_dm = dn if (dn > up and dn > 0) else 0
        plus_dm.append(p_dm)
        minus_dm.append(m_dm)
        tr_values.append(max(h[j]-l[j], abs(h[j]-c[j-1]), abs(l[j]-c[j-1])))
    
    atr = sum(tr_values)/len(tr_values)
    if atr <= 0:
        return 20.0
    plus_di = 100*sum(plus_dm)/atr
    minus_di = 100*sum(minus_dm)/atr
    dx = 100*abs(plus_di-minus_di)/(plus_di+minus_di) if (plus_di+minus_di) > 0 else 0
    
    # ADX = smoothed DX over another period
    adx_lookback = period
    if i < period*3:
        return dx
    dx_values = []
    for j in range(i-adx_lookback+1, i+1):
        p_dm2 = []
        m_dm2 = []
        tr2 = []
        for k in range(j-period+1, j+1):
            up = h[k]-h[k-1]
            dn = l[k-1]-l[k]
            p_dm2.append(up if (up > dn and up > 0) else 0)
            m_dm2.append(dn if (dn > up and dn > 0) else 0)
            tr2.append(max(h[k]-l[k], abs(h[k]-c[k-1]), abs(l[k]-c[k-1])))
        a2 = sum(tr2)/len(tr2) if tr2 else 1
        pdi = 100*sum(p_dm2)/a2 if a2 > 0 else 0
        mdi = 100*sum(m_dm2)/a2 if a2 > 0 else 0
        dxv = 100*abs(pdi-mdi)/(pdi+mdi) if (pdi+mdi) > 0 else 0
        dx_values.append(dxv)
    
    return float(sum(dx_values)/len(dx_values))

def get_regime(df, i):
    """Classify regime: COMPRESSION / TRENDING / RANGE / VOLATILITY_EXPANSION."""
    if i < 20:
        return 'UNKNOWN'
    feats = compute_features_local(df, i) if False else None
    # Simplile ADX-based regime
    adx = compute_adx(df, i)
    h = df['high'].values
    l = df['low'].values
    # ATR ratio
    tr20 = [max(h[j]-l[j], abs(h[j]-df['close'].iloc[j-1]), abs(l[j]-df['close'].iloc[j-1])) for j in range(i-19,i+1)]
    tr100 = [max(h[j]-l[j], abs(h[j]-df['close'].iloc[j-1]), abs(l[j]-df['close'].iloc[j-1])) for j in range(max(0,i-99),i+1)]
    atr_ratio = (sum(tr20)/len(tr20))/(sum(tr100)/len(tr100)) if tr100 else 1.0
    
    if atr_ratio < 0.7:
        return 'COMPRESSION'
    elif adx > 30:
        return 'TRENDING'
    elif adx < 20:
        return 'RANGE'
    else:
        return 'TRANSITION'

def compute_features_local(df, i):
    """Helper returning lightweight feature dict at i."""
    h = df['high'].values
    l = df['low'].values
    c = df['close'].values
    tr20 = [max(h[j]-l[j], abs(h[j]-df['close'].iloc[j-1]), abs(l[j]-df['close'].iloc[j-1])) for j in range(i-19,i+1)]
    tr100 = [max(h[j]-l[j], abs(h[j]-df['close'].iloc[j-1]), abs(l[j]-df['close'].iloc[j-1])) for j in range(max(0,i-99),i+1)]
    atr_ratio = (sum(tr20)/len(tr20))/(sum(tr100)/len(tr100)) if tr100 else 1.0
    return {'atr_ratio': atr_ratio}

# ============================================================
# EVENT DETECTION (COMPRESSION + FILTERED BY ADX/OI/FUNDING/REGIME)
# ============================================================
def detect_events(df, feats, 
                  compression_threshold=0.7, bb_threshold=0.05, vol_threshold=1.3,
                  adx_filter=None, oi_filter=None, regime_filter=None,
                  funding_filter=None):
    """Detect compression breakout events with optional filters."""
    setup_events = []
    trigger_events = []
    current_episode = None
    
    for i in range(20, len(df)):
        feat = feats[i]
        if feat is None:
            continue
        
        # Optional ADX filter
        if adx_filter is not None:
            if not adx_filter(feat['adx']):
                continue
        if oi_filter is not None:
            if not oi_filter(feat['oi_change_pct']):
                continue
        if regime_filter is not None:
            if feat['regime'] not in regime_filter:
                continue
        if funding_filter is not None:
            if not funding_filter(feat['funding']):
                continue
        
        is_compression = feat['atr_ratio'] < compression_threshold and feat['bb_width'] < bb_threshold
        
        if is_compression:
            if current_episode is None:
                current_episode = {
                    'episode_id': f"C{len(setup_events)+1:03d}",
                    'start_bar': i,
                    'direction': None,
                }
                setup_events.append({
                    'episode_id': current_episode['episode_id'],
                    'bar_idx': i,
                    'compression': feat['atr_ratio'],
                    'bb_width': feat['bb_width'],
                    'adx': feat['adx'],
                    'oi_change_pct': feat['oi_change_pct'],
                    'funding': feat['funding'],
                    'regime': feat['regime'],
                })
        else:
            if current_episode is not None:
                ep_high = max(df['high'].iloc[current_episode['start_bar']:i+1])
                ep_low = min(df['low'].iloc[current_episode['start_bar']:i+1])
                feat_vol = feat['volume_ratio']
                
                direction = None
                if df['close'].iloc[i] > ep_high * 1.001 and feat_vol > vol_threshold:
                    direction = 'LONG'
                elif df['close'].iloc[i] < ep_low * 0.999 and feat_vol > vol_threshold:
                    direction = 'SHORT'
                
                if direction:
                    trigger_events.append({
                        'episode_id': current_episode['episode_id'],
                        'bar_idx': i,
                        'direction': direction,
                        'volume_ratio': feat_vol,
                        'compression': feat['atr_ratio'],
                        'bb_width': feat['bb_width'],
                        'adx': feat['adx'],
                        'oi_change_pct': feat['oi_change_pct'],
                        'funding': feat['funding'],
                        'regime': feat['regime'],
                    })
                    current_episode = None
                elif i - current_episode['start_bar'] > 50:
                    current_episode = None
    
    return setup_events, trigger_events

# ============================================================
# FORWARD OUTCOMES + STATISTICS
# ============================================================
def compute_forward_outcomes(df, trigger_events, horizons=[1,3,6,12,24]):
    outcomes = []
    closes = df['close'].values
    for ev in trigger_events:
        i = ev['bar_idx']
        entry = closes[i]
        direction = ev['direction']
        fwd = dict(ev)
        fwd['event_id'] = f"{ev['episode_id']}_{i}"
        for h in horizons:
            j = min(i+h, len(closes)-1)
            ret = (closes[j]/entry - 1)*100
            if direction == 'SHORT':
                ret = -ret
            fwd[f'forward_{h}bar'] = round(ret,4)
        # MFE/MAE
        for h in horizons:
            end = min(i+h, len(closes)-1)
            mfe_exc, mae_exc = 0, 0
            for k in range(i, end+1):
                r = (closes[k]/entry - 1)*100
                if direction == 'SHORT': r = -r
                mfe_exc = max(mfe_exc, r)
                mae_exc = min(mae_exc, r)
            fwd[f'mfe_{h}bar'] = round(mfe_exc,4)
            fwd[f'mae_{h}bar'] = round(mae_exc,4)
        outcomes.append(fwd)
    return outcomes

def permutation_test(comp_fwd, baseline_fwd, n_iter=1000):
    n_c, n_b = len(comp_fwd), len(baseline_fwd)
    if n_c == 0 or n_b == 0:
        return None
    c = [1 if f.get('forward_1bar',0) > 0 else 0 for f in comp_fwd]
    b = [1 if f.get('forward_1bar',0) > 0 else 0 for f in baseline_fwd]
    obs_diff = (sum(c)/n_c) - (sum(b)/n_b)
    pooled = c + b
    count = 0
    for _ in range(n_iter):
        random.shuffle(pooled)
        diff = (sum(pooled[:n_c])/n_c) - (sum(pooled[n_c:])/n_b)
        if abs(diff) >= abs(obs_diff):
            count += 1
    return count/n_iter

def effect_size(comp_fwd, baseline_fwd):
    n_c, n_b = len(comp_fwd), len(baseline_fwd)
    if n_c == 0 or n_b == 0:
        return None
    p_c = sum(1 for f in comp_fwd if f.get('forward_1bar',0)>0)/n_c
    p_b = sum(1 for f in baseline_fwd if f.get('forward_1bar',0)>0)/n_b
    abs_delta = (p_c-p_b)*100
    rel_lift = (p_c-p_b)/p_b*100 if p_b>0 else None
    odds_c = p_c/(1-p_c) if p_c<1 else float('inf')
    odds_b = p_b/(1-p_b) if p_b<1 else float('inf')
    odds_ratio = odds_c/odds_b if odds_b>0 else None
    return {
        'p_compression': round(p_c,4), 'p_baseline': round(p_b,4),
        'absolute_delta_pp': round(abs_delta,2),
        'relative_lift_pct': round(rel_lift,2) if rel_lift else None,
        'odds_ratio': round(odds_ratio,3) if odds_ratio else None,
        'n_compression': n_c, 'n_baseline': n_b,
    }

def make_decision(effect, p_value, n_events, n_episodes, longs, shorts, economic):
    if effect is None or n_events == 0:
        return {'state':'INCONCLUSIVE','reason':'No events','level':0}
    abs_delta = effect['absolute_delta_pp']
    p_sig = p_value if p_value is not None else 1.0
    net_exp = economic.get('net_expectancy',0)
    net_pf = economic.get('net_pf',0)
    if p_sig > 0.05 or abs_delta < 2.0:
        return {'state':'INCONCLUSIVE',
                'reason':f'Not significant (p={p_sig:.3f}) or effect small (delta={abs_delta:.1f}pp)','level':1}
    if net_exp > 0 and abs_delta >= 2.0:
        return {'state':'HYPOTHESIS_SUPPORTED',
                'reason':f'Significant effect (delta={abs_delta:.1f}pp, p={p_sig:.3f}), positive net exp','level':2}
    if net_exp > 0 and net_pf > 1.2 and n_episodes >= 3:
        return {'state':'ROBUST_CANDIDATE',
                'reason':f'Robust (delta={abs_delta:.1f}pp), PF={net_pf:.2f}, {n_episodes} eps','level':3}
    if net_exp > 0.05 and net_pf > 1.5 and n_events >= 50:
        return {'state':'PRODUCTION_CANDIDATE',
                'reason':f'Production ready (delta={abs_delta:.1f}pp, PF={net_pf:.2f})','level':4}
    return {'state':'HYPOTHESIS_SUPPORTED','reason':f'Supported (delta={abs_delta:.1f}pp)','level':2}

# ============================================================
# MAIN
# ============================================================
print("="*70)
print("P1.7 REFINEMENT - WITH OI + ADX + REGIME + FUNDING")
print("="*70)

symbols = ['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','XRPUSDT']
all_triggers = []
all_df = {}

for symbol in symbols:
    df = load_symbol(symbol)
    if df is None:
        print(f"  [!] {symbol} skip"); continue
    all_df[symbol] = df
    feats = compute_features(df)
    
    # BASELINE: no filter (all compression)
    setup_base, trig_base = detect_events(df, feats)
    # FILTERED: ADX trending + OI increasing + regime compression
    setup_f, trig_f = detect_events(df, feats,
        adx_filter=lambda a: a > 25,
        oi_filter=lambda oi: oi > -0.5,
        regime_filter=['COMPRESSION','TRENDING'])
    
    print(f"\n--- {symbol} ---")
    print(f"  Bars: {len(df)}, Setup(base): {len(setup_base)}, Trigger(base): {len(trig_base)}")
    print(f"  Trigger(ADX+OI+regime filtered): {len(trig_f)}")
    
    outs = compute_forward_outcomes(df, trig_f)
    for o in outs:
        o['symbol'] = symbol
    all_triggers.extend(outs)

print("\n"+"="*70)
print(f"TOTAL FILTERED TRIGGERS: {len(all_triggers)} (with ADX+OI+regime filter)")
print("="*70)

longs = [t for t in all_triggers if t['direction']=='LONG']
shorts = [t for t in all_triggers if t['direction']=='SHORT']
print(f"LONG: {len(longs)}, SHORT: {len(shorts)}")

# Feature distribution of triggers
regimes = {}
for t in all_triggers:
    r = t['regime']
    regimes[r] = regimes.get(r,0)+1
print(f"Regime dist: {regimes}")

# Forward outcomes
print("\n--- FORWARD OUTCOME (FILTERED) ---")
for h in [1,3,6,12,24]:
    rets = [t.get(f'forward_{h}bar',0) for t in all_triggers]
    if rets:
        pos = sum(1 for r in rets if r>0)
        print(f"  {h}bar: mean={sum(rets)/len(rets):.3f}%, pos%={pos/len(rets)*100:.1f}% (n={len(rets)})")

# Baseline (random non-compression)
random.seed(123)
baseline_fwd = []
for _ in range(len(all_triggers)):
    sym = random.choice(list(all_df.keys()))
    d = all_df[sym]
    ri = random.randint(50, len(d)-30)
    entry = d['close'].iloc[ri]
    direction = random.choice(['LONG','SHORT'])
    ret = (d['close'].iloc[ri+1]/entry-1)*100
    if direction=='SHORT': ret=-ret
    baseline_fwd.append({'forward_1bar':ret})

effect = effect_size(all_triggers, baseline_fwd)
p_value = permutation_test(all_triggers, baseline_fwd)
print("\n--- EFFECT SIZE (FILTERED) ---")
if effect:
    print(f"  P(breakout|compression): {effect['p_compression']*100:.1f}% (n={effect['n_compression']})")
    print(f"  P(breakout|baseline):    {effect['p_baseline']*100:.1f}% (n={effect['n_baseline']})")
    print(f"  Abs delta: {effect['absolute_delta_pp']:+.1f} pp")
    if effect['relative_lift_pct']: print(f"  Rel lift: {effect['relative_lift_pct']:+.1f}%")
    if effect['odds_ratio']: print(f"  Odds ratio: {effect['odds_ratio']:.2f}")
print(f"  Permutation p: {p_value:.4f}")

# Economic
fee_rate = 0.0008
gross = sum(t.get('forward_1bar',0) for t in all_triggers)/len(all_triggers) if all_triggers else 0
net = gross - fee_rate*100
wins = [t['forward_1bar'] for t in all_triggers if t.get('forward_1bar',0)>0]
losses = [t['forward_1bar'] for t in all_triggers if t.get('forward_1bar',0)<=0]
net_pf = (sum(wins)-fee_rate*100*len(wins))/(-sum(losses)+fee_rate*100*len(losses)) if losses else 0
print(f"\n--- ECONOMIC ---")
print(f"  Gross exp: {gross:+.3f}%, Net exp: {net:+.3f}%, Net PF: {net_pf:.3f}")
economic = {'gross_expectancy':gross,'net_expectancy':net,'net_pf':net_pf,'fee_rate':fee_rate}

decision = make_decision(effect, p_value, len(all_triggers),
    len(set(t['episode_id'] for t in all_triggers)), len(longs), len(shorts), economic)
print(f"\n--- DECISION ---")
print(f"  State: {decision['state']}")
print(f"  Reason: {decision['reason']}")
print(f"  Level: {decision['level']}/4")

# Save
manifest = {
    'research_id':'CB-P1.7-RW-OIADX-001',
    'status':'P1_7_COMPLETE',
    'data_source':'Bot-Multi-Edge-metrics',
    'universe':symbols,
    'timeframes':['1h'],
    'n_events_total':len(all_triggers),
    'n_long':len(longs),'n_short':len(shorts),
    'filters':{'adx':'>25','oi':'>-0.5%','regime':['COMPRESSION','TRENDING']},
    'effect_size':effect,
    'permutation_pvalue':p_value,
    'regime_distribution':regimes,
    'decision':decision['state'],
    'decision_reason':decision['reason'],
    'economic':economic,
    'corrections_applied':19,
    'framework_version':'v2.1-OI-ADX-REGIME'
}
with open(os.path.join(RESEARCH_DIR,'research_manifest.json'),'w') as f:
    json.dump(manifest,f,indent=2)
with open(os.path.join(RESEARCH_DIR,'forward_outcomes.json'),'w') as f:
    json.dump(all_triggers,f,indent=2)

print("\n"+ "="*70)
print("SAVED. FINAL DECISION:", decision['state'])
print("="*70)
