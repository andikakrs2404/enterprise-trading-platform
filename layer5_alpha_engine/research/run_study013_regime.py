#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-013 — RS Regime Directionality (ex-ante measurable states)
=================================================================
Preregistered: H0=no prediction, H1=measurable state predicts RS direction.

3 states (LAGGED 24h, no forward-looking):
  S1: Breadth — % alt with ret24>0 (timestamp-by-timestamp)
  S2: Dispersion — std(ret24) across symbols
  S3: Index trend — mean(alt ret24) > 0?

Gate: state predicts RS spread Q5-Q1 conditionally.
"""
import json, os
import pandas as pd, numpy as np

DATA='/home/rtk/Bot-Multi-Edge-metrics/data'
KDIR=DATA+'/klines'
OUT='/home/rtk/enterprise-trading-platform/layer5_alpha_engine/research'

ALT_ONLY=True  # exclude BTC/ETH from universe (alpha on altcoins)

def load(sym):
    k=os.path.join(KDIR,sym,'klines_1h.parquet')
    if not os.path.exists(k): return None
    df=pd.read_parquet(k)[['close']].copy()
    df=df.rename_axis('ts').reset_index()
    df['ts']=pd.to_datetime(df['ts'],utc=True)
    df['ret24']=df['close'].pct_change(24)
    df['R24']=(df['close'].shift(-24)/df['close']-1)*100
    df['sym']=sym
    return df

print("="*70)
print("STUDY-013 — RS Regime Directionality (3 states, lagged 24h)")
print("="*70)

frames=[]
for sym in sorted(os.listdir(KDIR)):
    df=load(sym)
    if df is not None: frames.append(df)
all_df=pd.concat(frames,ignore_index=True).sort_values(['sym','ts']).reset_index(drop=True)

ts_count=all_df.groupby('ts').size()
valid=ts_count[ts_count>=10].index
all_df=all_df[all_df['ts'].isin(valid)].dropna(subset=['ret24','R24']).copy()

# RS rank
all_df['rs_rank']=all_df.groupby('ts')['ret24'].rank(pct=True)

# ================================================================
# MARKET STATE computation (timestamp-by-timestamp, all symbols)
# ================================================================
print("\nComputing market states (timestamp-by-timestamp)...")

if ALT_ONLY:
    ms=all_df[~all_df['sym'].isin(['BTCUSDT','ETHUSDT'])].copy()
else:
    ms=all_df.copy()

ts_state=ms.groupby('ts').agg(
    ret24_all=('ret24','mean'),     # S3: index trend (mean)
    ret24_std=('ret24','std'),      # S2: dispersion
    n_sym=('sym','count'),
).reset_index()

# S1: Breadth (% alt with ret24 > 0)
breadth=ms.assign(pos=(ms['ret24']>0).astype(float)).groupby('ts')['pos'].mean().reset_index()
breadth.columns=['ts','breadth']
ts_state=ts_state.merge(breadth,on='ts')

# LAG everything 24h
ts_state=ts_state.sort_values('ts').reset_index(drop=True)
ts_state['breadth_lag']=ts_state['breadth'].shift(24)
ts_state['disp_lag']=ts_state['ret24_std'].shift(24)
ts_state['trend_lag']=ts_state['ret24_all'].shift(24)
ts_state=ts_state.dropna(subset=['breadth_lag','disp_lag','trend_lag'])
print(f"  After lag: {len(ts_state)} periods, range {ts_state['ts'].min()} → {ts_state['ts'].max()}")

# Splits
n=len(ts_state)
ts_state['split']=''
ts_state.loc[:int(n*0.6),'split']='train'
ts_state.loc[int(n*0.6):int(n*0.8),'split']='val'
ts_state.loc[int(n*0.8):,'split']='test'
ts_state['year']=ts_state['ts'].dt.year

# Median split
ts_state['breadth_state']=np.where(ts_state['breadth_lag']>=ts_state['breadth_lag'].median(),'HIGH','LOW')
ts_state['disp_state']=np.where(ts_state['disp_lag']>=ts_state['disp_lag'].median(),'HIGH','LOW')
ts_state['trend_state']=np.where(ts_state['trend_lag']>=0,'POS','NEG')

# ================================================================
# RS spread Q5-Q1 R24 PER STATE
# ================================================================
print("\n" + "="*70)
print("STATE 1: MARKET BREADTH (lagged 24h) — % alt ret24>0")
print("="*70)

for state_name,col,states in [
    ('Breadth','breadth_state',['LOW','HIGH']),
    ('Dispersion','disp_state',['LOW','HIGH']),
    ('Index Trend','trend_state',['NEG','POS']),
]:
    print(f"\n--- {state_name} ---")
    print(f"  {'Split':<7}{'State':<7}{'Q1':>8}{'Q5':>8}{'Spread':>8}{'breadth':>9}{'n':>5}")
    for s in ['train','val','test','ALL']:
        sub=ts_state[ts_state['split']==s] if s!='ALL' else ts_state
        for st in states:
            ts_set=set(sub[sub[col]==st]['ts'])
            d=all_df[all_df['ts'].isin(ts_set)]
            q1=d[d['rs_rank']<0.2]['R24'].mean()*100
            q5=d[d['rs_rank']>0.8]['R24'].mean()*100
            # breadth: % symbols where Q5 outperforms
            sym_q5=d[d['rs_rank']>0.8].groupby('sym')['R24'].mean()
            sym_q1=d[d['rs_rank']<0.2].groupby('sym')['R24'].mean()
            common=sym_q5.index.intersection(sym_q1.index)
            brea=(sym_q5[common]>sym_q1[common]).sum()/len(common)*100 if len(common)>0 else 0
            print(f"  {s:<7}{st:<7}{q1:>+8.2f}{q5:>+8.2f}{q5-q1:>+8.2f}{brea:>8.0f}%{len(ts_set):>5}")

# ================================================================
# PER YEAR per STATE (critical temporal evidence)
# ================================================================
print("\n" + "="*70)
print("PER YEAR — RS spread per STATE (non-overlap temporal evidence)")
print("="*70)

for state_name,col in [('Breadth','breadth_state'),('Dispersion','disp_state'),('Trend','trend_state')]:
    print(f"\n--- {state_name} ---")
    print(f"  {'Year':<6}{'Low/Neg':>10}{'High/Pos':>10}{'Low n':>7}{'High n':>7}")
    for y in [2024,2025,2026]:
        sub=ts_state[(ts_state['year']==y)]
        for sti,st in enumerate(['LOW' if col!='trend_state' else 'NEG',
                                  'HIGH' if col!='trend_state' else 'POS']):
            ts_set=set(sub[sub[col]==st]['ts'])
            d=all_df[all_df['ts'].isin(ts_set)]
            q1=d[d['rs_rank']<0.2]['R24'].mean()*100
            q5=d[d['rs_rank']>0.8]['R24'].mean()*100
            sp=q5-q1; nn=len(ts_set)
            if sti==0:
                row=f"  {y:<6}{sp:>+10.2f}"
            else:
                row+=f"{sp:>+10.2f}{nn:>7}"
        # also print low state n
        ts_lo=set(sub[sub[col]==('LOW' if col!='trend_state' else 'NEG')]['ts'])
        row=f"  {y:<6}{q5-q1:>+10.2f}" # placeholder, recompute properly
        ts_lo_set=set(sub[sub[col]==('LOW' if col!='trend_state' else 'NEG')]['ts'])
        ts_hi_set=set(sub[sub[col]==('HIGH' if col!='trend_state' else 'POS')]['ts'])
        d_lo=all_df[all_df['ts'].isin(ts_lo_set)]
        d_hi=all_df[all_df['ts'].isin(ts_hi_set)]
        sp_lo=d_lo[d_lo['rs_rank']>0.8]['R24'].mean()*100-d_lo[d_lo['rs_rank']<0.2]['R24'].mean()*100
        sp_hi=d_hi[d_hi['rs_rank']>0.8]['R24'].mean()*100-d_hi[d_hi['rs_rank']<0.2]['R24'].mean()*100
        print(f"  {y:<6}{sp_lo:>+10.2f}{sp_hi:>+10.2f}{len(ts_lo_set):>7}{len(ts_hi_set):>7}")

# ================================================================
# INTERACTION: state adds info on top of RS?
# ================================================================
print("\n" + "="*70)
print("INTERACTION — does state ADD information to RS spread?")
print("="*70)
for state_name,col,states in [
    ('Breadth','breadth_state',['LOW','HIGH']),
    ('Dispersion','disp_state',['LOW','HIGH']),
    ('Trend','trend_state',['NEG','POS']),
]:
    # unconditional RS spread
    d_all=all_df.copy()
    sp_uncond=d_all[d_all['rs_rank']>0.8]['R24'].mean()*100-d_all[d_all['rs_rank']<0.2]['R24'].mean()*100
    spreads=[]
    for st in states:
        ts_set=set(ts_state[ts_state[col]==st]['ts'])
        d=all_df[all_df['ts'].isin(ts_set)]
        sp=d[d['rs_rank']>0.8]['R24'].mean()*100-d[d['rs_rank']<0.2]['R24'].mean()*100
        spreads.append(sp)
    delta=max(spreads)-min(spreads)
    print(f"  {state_name:<12} unconditional={sp_uncond:+.2f}bps  "
          f"{states[0]}={spreads[0]:+.2f} {states[1]}={spreads[1]:+.2f}  delta={delta:+.2f}bps")

# ================================================================
# NET @ 12bps per state (best state only)
# ================================================================
print("\n" + "="*70)
print("NET @ 12bps per state (R24 horizon, full sample)")
print("="*70)
for state_name,col,states in [
    ('Breadth','breadth_state',['LOW','HIGH']),
    ('Dispersion','disp_state',['LOW','HIGH']),
    ('Trend','trend_state',['NEG','POS']),
]:
    print(f"\n  {state_name}:")
    for st in states:
        ts_set=set(ts_state[ts_state[col]==st]['ts'])
        d=all_df[all_df['ts'].isin(ts_set)]
        q1=d[d['rs_rank']<0.2]['R24'].mean()*100
        q5=d[d['rs_rank']>0.8]['R24'].mean()*100
        gross=q5-q1
        # assuming ~1 rebalance per 24h, turnover ~30% (from Q5 churn)
        net=gross-0.30*12
        print(f"    {st}: gross={gross:+.2f}bps net@12={net:+.2f}bps coverage={len(ts_set)} periods")

# ================================================================
# VERDICT per failure criteria
# ================================================================
print("\n" + "="*70)
print("VERDICT (failure criteria A-D)")
print("="*70)
print("  (A) Conditional spread ≈ 0 → check table above")
print("  (B) Consistent TRAIN/VAL/TEST → check per-year + per-split")
print("  (C) Coverage <10% → check period counts")
print("  (D) Net@12 <0 → check net table")

report={'study':'STUDY-013','states':['breadth_lag','disp_lag','trend_lag']}
with open(os.path.join(OUT,'STUDY-013_REGIME.json'),'w') as f:
    json.dump(report,f,indent=2,default=str)
print(f"\nSaved: research/STUDY-013_REGIME.json")
print("="*70)