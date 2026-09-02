#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-006 PHASE B — Preregistered Cross-Sectional RS Verification
=================================================================
PRE-REGISTERED DEFINISI (dikunci, TIDAK diubah):
  - Momentum: ret_24h (rank pct cross-sectional per timestamp)
  - Q5 = top 20% rank, Q1 = bottom 20%
  - Dispersion: cross-sectional 90-10 percentile spread of ret_24h per timestamp
  - HIGH dispersion = spread > global median (dibekukan DI SINI, tidak dioptimasi)

Hipotesis (preregistered):
  H1: Q5 momentum spread (Q5-Q1) > 0 lintas waktu
  H2: Q5-Q1 spread lebih besar di HIGH dispersion vs LOW dispersion
  H3: temporal stability (2024 / 2025 / 2026 konsisten)
  H4: symbol stability (mayoritas symbol Q5 > Q1)
  H5: net-after-cost pada spread Q5-Q1
  H6: effect decay R6/R12/R24/R48/R72

TIDAK melakukan: threshold optimization, filter atas, regime tightening.
"""
import json, os, random, statistics
import pandas as pd, numpy as np
random.seed(42); np.random.seed(42)

DATA='/home/rtk/Bot-Multi-Edge-metrics/data'
KDIR=DATA+'/klines'
OUT='/home/rtk/enterprise-trading-platform/layer5_alpha_engine/research'

def load(sym):
    k=os.path.join(KDIR,sym,'klines_1h.parquet')
    if not os.path.exists(k): return None
    df=pd.read_parquet(k)[['open','high','low','close','volume']].copy()
    df.index=pd.to_datetime(df.index,utc=True)
    return df

print("="*70)
print("STUDY-006 PHASE B — Preregistered Cross-Sectional RS")
print("Definisi dikunci. Tidak ada threshold optimasi.")
print("="*70)

syms=sorted(os.listdir(KDIR))
frames=[]
for sym in syms:
    df=load(sym)
    if df is None: continue
    df['sym']=sym
    df['ret_24h']=df['close'].pct_change(24)
    df['vol_24h']=df['close'].pct_change().rolling(24).std()
    for h in [6,12,24,48,72]:
        df[f'R{h}']=(df['close'].shift(-h)/df['close']-1)*100
    frames.append(df)

all_df=pd.concat(frames)
all_df=all_df.dropna(subset=['ret_24h','vol_24h','R6','R12','R24','R48','R72'])
print(f"Clean rows: {len(all_df)}")

# Cross-sectional rank & dispersion per timestamp in ONE groupby to align
ts=all_df.groupby(all_df.index)
# Rank momentum
all_df['mom_rank']=ts['ret_24h'].rank(pct=True)
# Dispersion per timestamp (90-10 spread of ret_24h)
disp=ts['ret_24h'].agg(lambda x: x.quantile(0.9)-x.quantile(0.1))
# Join dispersion back
all_df['disp']=all_df.index.map(dict(disp))
# THRESHOLD DI FREEZE: high dispersion = disp > median (dari FULL data, dikunci ex-ante)
disp_med=disp.median()
all_df['disp_state']=np.where(all_df['disp']>disp_med,'HIGH','LOW')
print(f"Dispersion median (frozen, ex-ante): {disp_med:.5f}")

# Define quintiles FROZEN: Q5 top20, Q1 bottom20
all_df['Q']=pd.qcut(all_df['mom_rank'],5,labels=['Q1','Q2','Q3','Q4','Q5'])
# year
all_df['year']=all_df.index.year
# Only need timestamps with enough symbols
ts_count=ts.size()
all_df=all_df[all_df.index.isin(ts_count[ts_count>=10].index)]
print(f"Rows after ≥10 sym/ts filter: {len(all_df)}")

# ================================================================
# Helper: spread Q5-Q1 for a subset
# ================================================================
def spread(sub):
    q5=sub[sub['Q']=='Q5']['R24'].mean()
    q1=sub[sub['Q']=='Q1']['R24'].mean()
    if np.isnan(q5) or np.isnan(q1): return None, None, None
    return q5-q1, q5, q1

# ================================================================
# H1: Overall Q5-Q1 spread
# ================================================================
print("\n"+"="*70)
print("H1: Overall growth spread (Q5-Q1) — full data")
print("="*70)
s, q5, q1 = spread(all_df)
print(f"  Q5={q5:+.4f}%, Q1={q1:+.4f}%, Spread={s:+.4f}%")
print(f"  H1 ({s}>0): {'PASS' if s>0 else 'FAIL'}")

# ================================================================
# H2: High vs Low dispersion
# ================================================================
print("\n"+"="*70)
print("H2: Q5-Q1 spread — HIGH vs LOW dispersion (frozen threshold)")
print("="*70)
hi=all_df[all_df['disp_state']=='HIGH']
lo=all_df[all_df['disp_state']=='LOW']
s_hi, q5_hi, q1_hi = spread(hi)
s_lo, q5_lo, q1_lo = spread(lo)
print(f"  HIGH disp: Q5={q5_hi:+.4f}%, Q1={q1_hi:+.4f}%, Spread={s_hi:+.4f}% (n={len(hi)})")
print(f"  LOW disp:  Q5={q5_lo:+.4f}%, Q1={q1_lo:+.4f}%, Spread={s_lo:+.4f}% (n={len(lo)})")
print(f"  H2 (HIGH>LOW): {'PASS' if s_hi>s_lo else 'FAIL'}")

# ================================================================
# H3: Temporal stability by year
# ================================================================
print("\n"+"="*70)
print("H3: Temporal stability (per year) — spread per year")
print("="*70)
for yr in sorted(all_df['year'].unique()):
    sub=all_df[all_df['year']==yr]
    s_yr,_,_=spread(sub)
    s_hi_yr,_,_=spread(sub[sub['disp_state']=='HIGH'])
    print(f"  {yr}: spread={s_yr:+.4f}%, HIGH-disp spread={s_hi_yr:+.4f}% (n={len(sub)})")

# ================================================================
# H4: Symbol stability
# ================================================================
print("\n"+"="*70)
print("H4: Symbol stability (berapa % simbool Q5>Q1 untuk R24)")
print("="*70)
pos=0; neg=0; total=0
for sym in all_df['sym'].unique():
    sub=all_df[all_df['sym']==sym]
    s_sym,_,_=spread(sub)
    if s_sym is None: continue
    total+=1
    if s_sym>0: pos+=1
    else: neg+=1
print(f"  Q5>Q1: {pos}/{total} symbol ({pos/total*100:.0f}%)")
print(f"  H4 ({pos/total>0.5}): {'PASS' if pos/total>0.5 else 'FAIL'}")

# ================================================================
# H5: Net-after-cost (Q5-Q1 spread, R24, 8bps)
# ================================================================
print("\n"+"="*70)
print("H5: Net-after-cost (Q5-Q1 spread, round-trip)")
print("="*70)
# Long Q5 best 20%, short Q1 worst 20% - equal weight
q5_sub=all_df[all_df['Q']=='Q5']['R24'].mean()
q1_sub=all_df[all_df['Q']=='Q1']['R24'].mean()
gross_net=s
for fee in [8,10,12]:
    net=s-fee*2/100  # fee in bps -> % ; round trip 2x
    print(f"  Fee {fee}bps: net spread={net:+.4f}% ({net*100:.1f}bps) -> {'POSITIF' if net>0 else 'NEGATIF'}")

# ================================================================
# H6: Effect decay R6/R12/R24/R48/R72
# ================================================================
print("\n"+"="*70)
print("H6: Effect decay (spread per horizon)")
print("="*70)
print(f"  {'horizon':<8}{'Q5':>10}{'Q1':>10}{'spread':>10}")
for h in ['R6','R12','R24','R48','R72']:
    q5h=all_df[all_df['Q']=='Q5'][h].mean()
    q1h=all_df[all_df['Q']=='Q1'][h].mean()
    sh=q5h-q1h
    print(f"  {h:<8}{q5h:>+10.4f}{q1h:>+10.4f}{sh:>+10.4f}")

# ================================================================
# MTC: multiple testing (Q5 across horizons)
# ================================================================
print("\n"+"="*70)
print("MTC: multiple testing note")
print("="*70)
print("  7 horizons x 2 dispersion states diuji -> jumlah eksplorasi dicatat")
print("  Jika klaim statistik, lakukan FDR/Bonferroni eksplisit di dokumentasi")

# Save
report={
    'study':'STUDY-006-PHASE-B','preregistered':True,'parent':'STUDY-006-PHASE-A',
    'definitions_frozen':{'momentum':'ret_24h_rank','disp_hi':'disp>median (frozen)','Q':'top20/bottom20'},
    'H1':{'spread':round(s,4) if s else None,'pass':bool(s and s>0)},
    'H2':{'high':round(s_hi,4) if s_hi else None,'low':round(s_lo,4) if s_lo else None,'pass':bool(s_hi and s_lo and s_hi>s_lo)},
    'H4':{'pos_symbols':pos,'total':total,'pct':round(pos/total*100,1) if total else 0},
    'H5':{'gross_spread_bps':round(s*100,1) if s else None,
          'net8_bps':round(s*100-16,1) if s else None,
          'net10_bps':round(s*100-20,1) if s else None,
          'net12_bps':round(s*100-24,1) if s else None},
    'H6_decay':{h:round(float(all_df[all_df['Q']=='Q5'][h].mean()-all_df[all_df['Q']=='Q1'][h].mean()),4) for h in ['R6','R12','R24','R48','R72']},
    'label':'Preregistered Hypothesis Validation — BUKAN edge/live',
    'verdict':'Phase B preregistered result (bukan final alpha)'}
with open(os.path.join(OUT,'STUDY-006_PHASE_B.json'),'w') as f:
    json.dump(report,f,indent=2,default=str)
print("\nSaved: research/STUDY-006_PHASE_B.json")
print("STUDY-006 Phase B SELESAI")
print("="*70)
