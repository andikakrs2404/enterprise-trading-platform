#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-008C — ΔOI_share_7d Temporal Stability Investigation
===========================================================
INVESTIGASI, bukan validasi alpha.
Preregistered H1-H4.
"""
import json, os, random
import pandas as pd, numpy as np
random.seed(42); np.random.seed(42)

DATA='/home/rtk/Bot-Multi-Edge-metrics/data'
KDIR=DATA+'/klines'; MDIR=DATA+'/metrics'
OUT='/home/rtk/enterprise-trading-platform/layer5_alpha_engine/research'

def load(sym):
    k=os.path.join(KDIR,sym,'klines_1h.parquet')
    m=os.path.join(MDIR,sym,'metrics_1h.parquet')
    if not os.path.exists(k): return None
    df=pd.read_parquet(k)[['open','high','low','close','volume']].copy()
    df.index=pd.to_datetime(df.index,utc=True)
    if os.path.exists(m):
        met=pd.read_parquet(m); met.index=pd.to_datetime(met.index,utc=True)
        df=df.join(met[['sum_open_interest']],how='left')
    else: df['sum_open_interest']=np.nan
    df['sym']=sym
    return df

print("="*70)
print("STUDY-008C — Temporal Stability Investigation: ΔOI_share_7d → R72")
print("="*70)

syms=sorted(os.listdir(KDIR))
frames=[]
for sym in syms:
    df=load(sym)
    if df is None: continue
    df['R72']=(df['close'].shift(-72)/df['close']-1)*100
    df['ret24']=df['close'].pct_change(24)
    frames.append(df)

all_df=pd.concat(frames).sort_index()
ts=all_df.groupby(all_df.index)
all_df['vol_total']=ts['volume'].transform('sum')
all_df['oi_total']=ts['sum_open_interest'].transform('sum')
all_df['oi_share']=all_df['sum_open_interest']/all_df['oi_total']
all_df['d_oi_7d']=all_df.groupby('sym')['oi_share'].diff(168)
all_df['rs_rank']=ts['ret24'].rank(pct=True)

# Dispersion
disp=ts['ret24'].agg(lambda x: x.quantile(0.9)-x.quantile(0.1))
disp_med=disp.median()
all_df['disp_state']=all_df.index.map(lambda x: 'HIGH' if disp.get(x,0)>disp_med else 'LOW')

ts_count=ts.size()
all_df=all_df[all_df.index.isin(ts_count[ts_count>=10].index)]
dc=all_df.dropna(subset=['d_oi_7d','R72','rs_rank']).copy()
dc['oi_rank']=dc.groupby(dc.index)['d_oi_7d'].rank(pct=True)
dc['oi_q']=pd.qcut(dc['oi_rank'],5,labels=['Q1','Q2','Q3','Q4','Q5'])
dc['year']=dc.index.year
dc['month']=dc.index.to_period('M')
print(f"Rows: {len(dc)}, sym: {len(dc['sym'].unique())}")

def spread(sub, col='R72'):
    q5=sub[sub['oi_q']=='Q5'][col].mean()
    q1=sub[sub['oi_q']=='Q1'][col].mean()
    if np.isnan(q5) or np.isnan(q1): return None
    return q5-q1

# ================================================================
# H1: Monotonic improvement over time (per quarter)
# ================================================================
print("\n"+"="*70)
print("H1: EDGE OVER TIME (per quarter) — ΔOI_share_7d Q5-Q1 → R72")
print("="*70)
dc['quarter']=dc.index.to_period('Q')
quarters=sorted(dc['quarter'].unique())
q_data=[]
for q in quarters:
    sub=dc[dc['quarter']==q]
    s=spread(sub)
    if s is not None:
        q_data.append((str(q),s,len(sub)))
        print(f"  {q}: spread={s:+.4f}% (n={len(sub):>6})")
# Monotonicity check
if len(q_data)>1:
    vals=[x[1] for x in q_data]
    mono_up=sum(1 for i in range(len(vals)-1) if vals[i]<=vals[i+1])
    print(f"  Monotonic increase: {mono_up}/{len(vals)-1} steps")
    print(f"  → {'APPROACHING MONOTONIC ✅' if mono_up>=len(vals)*0.6 else 'NOT MONOTONIC'}")

# ================================================================
# H1b: Per year
# ================================================================
print("\n  --- Per year ---")
for yr in sorted(dc['year'].unique()):
    sub=dc[dc['year']==yr]
    s=spread(sub)
    print(f"  {yr}: spread={s:+.4f}% (n={len(sub):>7})")

# ================================================================
# H2: Leave-one-symbol-out
# ================================================================
print("\n"+"="*70)
print("H2: LEAVE-ONE-SYMBOL-OUT — ΔOI_share_7d Q5-Q1 → R72")
print("="*70)
base_spread=spread(dc)
print(f"  Full: spread={base_spread:+.4f}%")
sym_drops=[]
for sym in dc['sym'].unique():
    sub=dc[dc['sym']!=sym]
    s=spread(sub)
    if s is not None:
        sym_drops.append((sym,s,base_spread-s))
sym_drops_sorted=sorted(sym_drops,key=lambda x:x[2],reverse=True)
print(f"\n  Largest drops (most influential symbols):")
for sym,_,drop in sym_drops_sorted[:5]:
    print(f"    Excluding {sym}: drop={drop:+.4f}%")
print(f"\n  Smallest drops:")
for sym,_,drop in sym_drops_sorted[-3:]:
    print(f"    Excluding {sym}: drop={drop:+.4f}%")
mean_drop=np.mean([d[2] for d in sym_drops])
print(f"\n  Mean drop: {mean_drop:+.4f}%")
print(f"  Edge robust to symbol removal: {'YES ✅' if mean_drop<0.05 else 'CONCENTRATED ❌'}")

# ================================================================
# H3: Dispersion conditional (LOW vs HIGH)
# ================================================================
print("\n"+"="*70)
print("H3: DISPERSION CONDITIONAL — LOW vs HIGH")
print("="*70)
for ds in ['LOW','HIGH']:
    sub=dc[dc['disp_state']==ds]
    s=spread(sub)
    n5=len(sub[sub['oi_q']=='Q5'])
    n1=len(sub[sub['oi_q']=='Q1'])
    print(f"  {ds} dispersion: spread={s:+.4f}% (Q5 n={n5}, Q1 n={n1})")
low_s=spread(dc[dc['disp_state']=='LOW'])
high_s=spread(dc[dc['disp_state']=='HIGH'])
print(f"  → {'LOW > HIGH: hypothesis SUPPORTED ✅' if low_s>high_s else 'HIGH >= LOW: hypothesis NOT supported'}")

# ================================================================
# H4: Period emergence (2024 vs 2025+)
# ================================================================
print("\n"+"="*70)
print("H4: PERIOD EMERGENCE — 2024 vs 2025+")
print("="*70)
s2024=spread(dc[dc['year']==2024])
s2025p=spread(dc[dc['year']>=2025])
print(f"  2024:       spread={s2024:+.4f}%")
print(f"  2025+:      spread={s2025p:+.4f}%")
if s2024 is not None and s2025p is not None:
    print(f"  → {'Edge STRONGER in 2025+: hypothesis SUPPORTED ✅' if s2025p>s2024 else 'Edge NOT concentrated in 2025+'}")
    # Further breakdown
    for yr in [2025,2026]:
        sub=dc[dc['year']==yr]
        if len(sub)>0:
            s=spread(sub)
            print(f"  {yr}: spread={s:+.4f}% (n={len(sub):>7})")

# ================================================================
# H4b: Rolling window (quarterly)
# ================================================================
print("\n  --- Quarterly spread evolution ---")
for q in quarters:
    sub=dc[dc['quarter']==q]
    s=spread(sub)
    low_s=sub[sub['disp_state']=='LOW']
    high_s=sub[sub['disp_state']=='HIGH']
    sl=spread(low_s)
    sh=spread(high_s)
    print(f"  {q}: total={s:+.4f}%  LOW={sl:+.4f}%  HIGH={sh:+.4f}%  n={len(sub)}")

# ================================================================
# SAVE
# ================================================================
report={
    'study':'STUDY-008C-TEMPORAL-INVESTIGATION',
    'kandidat':'ΔOI_share_7d → R72',
    'H1_monotonic':{str(q):round(s,4) for q,s,_ in q_data},
    'H2_leave_one':{'mean_drop':round(float(mean_drop),4),'n_symbols':len(sym_drops)},
    'H3_dispersion':{'LOW':round(float(low_s),4) if low_s else None,'HIGH':round(float(high_s),4) if high_s else None},
    'H4_period':{'2024':round(float(s2024),4) if s2024 else None,'2025+':round(float(s2025p),4) if s2025p else None},
    'label':'Temporal Investigation — deskriptif, bukan alpha validation'}
with open(os.path.join(OUT,'STUDY-008C_TEMPORAL.json'),'w') as f:
    json.dump(report,f,indent=2,default=str)
print("\nSaved: research/STUDY-008C_TEMPORAL.json")
print("STUDY-008C SELESAI")
print("="*70)
