#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-002 VERIFICATION — Cross-Symbol Consistency + Event Distribution + Horizon Robustness
==========================================================================================
Status: masih eksplorasi (bukan pre-registration)
State yang diverifikasi: FUND_LOW + OI_LOW (dari Phase A)
Tujuan: memastikan fenomena TIDAK hanya didominasi beberapa simbol.
"""
import json, os, sys, math, random, statistics
import pyarrow.parquet as pq
import pandas as pd
import numpy as np

DATA_DIR='/home/rtk/Bot-Multi-Edge-metrics/data/klines'
MET_DIR='/home/rtk/Bot-Multi-Edge-metrics/data/metrics'
FUND_DIR='/home/rtk/Bot-Multi-Edge-metrics/data/funding'
RESEARCH_DIR='/home/rtk/enterprise-trading-platform/layer5_alpha_engine/research'
os.makedirs(RESEARCH_DIR, exist_ok=True)
random.seed(42); np.random.seed(42)

def load_symbol(symbol):
    k=os.path.join(DATA_DIR,symbol,'klines_1h.parquet')
    m=os.path.join(MET_DIR,symbol,'metrics_1h.parquet')
    f=os.path.join(FUND_DIR,symbol,'funding_1h.parquet')
    if not os.path.exists(k): return None
    df=pd.read_parquet(k)[['open','high','low','close','volume']].copy()
    df.index=pd.to_datetime(df.index,utc=True)
    if os.path.exists(m):
        met=pd.read_parquet(m); met.index=pd.to_datetime(met.index,utc=True)
        df=df.join(met[['sum_open_interest']],how='left')
    else: df['sum_open_interest']=np.nan
    if os.path.exists(f):
        fund=pd.read_parquet(f); fund.index=pd.to_datetime(fund.index,utc=True)
        df=df.join(fund[['funding_rate']],how='left')
    else: df['funding_rate']=np.nan
    return df

print("="*70)
print("STUDY-002 VERIFICATION — Cross-Symbol + Event Distribution + Horizon Robustness")
print("State: FUND_LOW + OI_LOW | Status: eksplorasi (bukan pre-registration)")
print("="*70)

symbols=sorted(os.listdir(DATA_DIR))
all_frames=[]
for symbol in symbols:
    df=load_symbol(symbol)
    if df is None: continue
    c=df['close']; out=pd.DataFrame(index=df.index)
    for h in [1,3,6,12,24]:
        out[f'R{h}']=(c.shift(-h)/c-1)*100
    out['symbol']=symbol
    out['oi_raw']=df['sum_open_interest']
    out['funding_raw']=df['funding_rate']
    out['price_return_1']=c.pct_change()*100
    all_frames.append(out.iloc[:-24])

all_df=pd.concat(all_frames)
all_df['funding_cs_pct']=all_df.groupby('symbol')['funding_raw'].rank(pct=True)
all_df['oi_cs_pct']=all_df.groupby('symbol')['oi_raw'].rank(pct=True)
df_clean=all_df.dropna(subset=['funding_cs_pct','oi_cs_pct','R1','R6','R12','R24'])
df_clean['OI_S']=pd.cut(df_clean['oi_cs_pct'],bins=[0,0.33,0.66,1.0],labels=['OI_LOW','OI_MID','OI_HIGH'],include_lowest=True)
df_clean['FD_S']=pd.cut(df_clean['funding_cs_pct'],bins=[0,0.33,0.66,1.0],labels=['FUND_LOW','FUND_MID','FUND_HIGH'],include_lowest=True)

target=df_clean[(df_clean['FD_S']=='FUND_LOW')&(df_clean['OI_S']=='OI_LOW')].copy()
print(f"\nTarget state FUND_LOW+OI_LOW: {len(target)} rows total")

# ================================================================
# VERIFICATION A — Cross-Symbol Consistency
# ================================================================
print("\n"+"="*70)
print("VERIFICATION A: Cross-Symbol Consistency (FUND_LOW+OI_LOW)")
print("="*70)

per_sym=[]
for sym in symbols:
    sub=target[target['symbol']==sym]
    if len(sub)==0: continue
    per_sym.append({
        'symbol':sym,
        'n':int(len(sub)),
        'R1':float(sub['R1'].mean()),
        'R6':float(sub['R6'].mean()),
        'R12':float(sub['R12'].mean()),
        'R24':float(sub['R24'].mean()),
    })

# Sort by R24
per_sym.sort(key=lambda x:x['R24'],reverse=True)
total_syms=len(per_sym)
n_pos_r24=sum(1 for s in per_sym if s['R24']>0)
n_neg_r24=sum(1 for s in per_sym if s['R24']<0)
r24_vals=[s['R24'] for s in per_sym]
median_r24=statistics.median(r24_vals)
mean_r24=statistics.mean(r24_vals)
sorted_r24=sorted(r24_vals)
iqr_lower=sorted_r24[int(total_syms*0.25)]
iqr_upper=sorted_r24[int(total_syms*0.75)]

print(f"\n  POSITIF: {n_pos_r24}/{total_syms} symbol (R24>0)")
print(f"  NEGATIF: {n_neg_r24}/{total_syms} symbol (R24<0)")
print(f"  Median R24 per symbol: {median_r24:+.4f}%")
print(f"  Mean R24 per symbol:   {mean_r24:+.4f}%")
print(f"  IQR: [{iqr_lower:+.4f}, {iqr_upper:+.4f}]")

print(f"\n  TOP 5 (R24 tertinggi):")
for s in per_sym[:5]:
    print(f"    {s['symbol']:<12} n={s['n']:>5}  R1={s['R1']:+.4f}  R6={s['R6']:+.4f}  R12={s['R12']:+.4f}  R24={s['R24']:+.4f}")
print(f"\n  BOTTOM 5 (R24 terendah):")
for s in per_sym[-5:]:
    print(f"    {s['symbol']:<12} n={s['n']:>5}  R1={s['R1']:+.4f}  R6={s['R6']:+.4f}  R12={s['R12']:+.4f}  R24={s['R24']:+.4f}")

# ================================================================
# VERIFICATION B — Event Distribution
# ================================================================
print("\n"+"="*70)
print("VERIFICATION B: Event Distribution per Symbol (FUND_LOW+OI_LOW)")
print("="*70)
ns=[s['n'] for s in per_sym]
print(f"  Total symbols: {len(ns)}")
print(f"  Min events:    {min(ns)} ({per_sym[ns.index(min(ns))]['symbol']})")
print(f"  Median events: {statistics.median(ns)}")
print(f"  Max events:    {max(ns)} ({per_sym[ns.index(max(ns))]['symbol']})")
print(f"  Mean events:   {statistics.mean(ns):.0f}")
print(f"  Sum:           {sum(ns)}")

# Apakah ada bias dari few symbols?
total_n=sum(ns)
top3_n=sorted(ns,reverse=True)[:3]
top3_pct=sum(top3_n)/total_n*100
print(f"  Top 3 symbols contribute {top3_pct:.1f}% of total events ({top3_n})")
print(f"  {'Top 3 = dominates' if top3_pct>50 else 'Top 3 = balanced'}")

# ================================================================
# VERIFICATION C — Horizon Robustness per Symbol
# ================================================================
print("\n"+"="*70)
print("VERIFICATION C: Horizon Robustness — pola R1<R6<R12<R24 per symbol?")
print("="*70)
n_monotonic=0
n_partial=0
n_none=0
detail=[]
for s in per_sym:
    r1,r6,r12,r24=s['R1'],s['R6'],s['R12'],s['R24']
    # Cek monotonisitas: R1 < R6 < R12 < R24 (semua naik)
    mono=(r1<r6<r12<r24)
    # Cek sebagian: R6<R12<R24 (trend naik di akhir)
    partial=(r6<r12<r24)
    if mono: n_monotonic+=1
    elif partial: n_partial+=1
    else: n_none+=1
    detail.append({'symbol':s['symbol'],'mono':mono,'partial':partial,
                   'R1':r1,'R6':r6,'R12':r12,'R24':r24})

print(f"  Fully monotonic (R1<R6<R12<R24): {n_monotonic}/{total_syms} symbol")
print(f"  Partially (R6<R12<R24 only):     {n_partial}/{total_syms} symbol")
print(f"  No upward pattern:               {n_none}/{total_syms} symbol")
print(f"  Dominant: {'MONOTONIC' if n_monotonic>n_partial+n_none else 'PARTIAL' if n_partial>n_none else 'NO PATTERN'}")

# Tampilkan semua symbol horizontal profile
print(f"\n  {'Symbol':<12}{'R1':>8}{'R6':>8}{'R12':>8}{'R24':>8}  Pattern")
print("  "+"-"*55)
for s in per_sym:
    r1,r6,r12,r24=s['R1'],s['R6'],s['R12'],s['R24']
    p='mono' if (r1<r6<r12<r24) else 'partial' if (r6<r12<r24) else 'flat'
    print(f"  {s['symbol']:<12}{r1:>+8.4f}{r6:>+8.4f}{r12:>+8.4f}{r24:>+8.4f}  {p}")

# ================================================================
# KESIMPULAN VERIFIKASI
# ================================================================
print("\n"+"="*70)
print("KESIMPULAN VERIFIKASI")
print("="*70)
verdict=''
if n_pos_r24 >= total_syms*0.6 and n_monotonic+n_partial >= total_syms*0.5:
    verdict='CANDIDATE PHENOMENON - layak di-pre-register Phase B'
elif n_pos_r24 >= total_syms*0.5:
    verdict='WEAK PHENOMENON - perlu lebih banyak data sebelum pre-register'
else:
    verdict='NO CLEAR PHENOMENON - tidak cukup bukti cross-symbol'
print(f"  {verdict}")
print(f"  Konsistensi: {n_pos_r24}/{total_syms} positive R24")
print(f"  Pola monotonik: {n_monotonic+partial}/{total_syms}")

result={
    'study':'STUDY-002-VERIFICATION',
    'state':'FUND_LOW+OI_LOW',
    'status':'eksplorasi (bukan pre-registration)',
    'cross_symbol':{'n_symbols':total_syms,'n_positive_R24':n_pos_r24,'n_negative_R24':n_neg_r24,
        'median_R24':round(median_r24,4),'mean_R24':round(mean_r24,4),'IQR':[round(iqr_lower,4),round(iqr_upper,4)],
        'top5':[{'sym':s['symbol'],'R24':round(s['R24'],4),'n':s['n']} for s in per_sym[:5]],
        'bottom5':[{'sym':s['symbol'],'R24':round(s['R24'],4),'n':s['n']} for s in per_sym[-5:]]},
    'event_distribution':{'min':min(ns),'median':statistics.median(ns),'max':max(ns),
        'mean':round(statistics.mean(ns),0),'top3_pct':round(top3_pct,1)},
    'horizon_robustness':{'fully_monotonic':n_monotonic,'partial':n_partial,'no_pattern':n_none},
    'verdict':verdict}
with open(os.path.join(RESEARCH_DIR,'STUDY-002_verification.json'),'w') as f:
    json.dump(result,f,indent=2,default=str)
print("\nSaved to research/STUDY-002_verification.json")
print("="*70)
