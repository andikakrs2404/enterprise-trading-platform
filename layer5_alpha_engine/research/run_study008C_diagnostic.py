#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-008C Diagnostik: Apakah 2024 reversal (Q1 menang) artifact atau nyata?
============================================================================
Menyelidiki:
1. Apakah Q1/Q5 di 2024 span symbol yang SAMA dengan 2025-2026?
   - 2024 mungkin punya sedikit simbol (alt belum listing)
2. Apakah pembagian quintile menghasilkan Q1/Q5 yang seimbang di 2024?
3. Apakah reversal 2024 datang dari subset simbol tertentu?
4. Independence check — R72 overlap (shift -72) membuat sampel tidak independent
5. Per-symbol: 2024 Q1 menang karena apa? (banyak simbol vs 1-2 outlier)
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
    df=pd.read_parquet(k)[['close','volume']].copy()
    df.index=pd.to_datetime(df.index,utc=True)
    if os.path.exists(m):
        met=pd.read_parquet(m); met.index=pd.to_datetime(met.index,utc=True)
        df=df.join(met[['sum_open_interest']],how='left')
    else: df['sum_open_interest']=np.nan
    df['sym']=sym; return df

print("="*70)
print("STUDY-008C DIAGNOSTIC — 2024 Reversal: Artifact atau Nyata?")
print("="*70)

frames=[]
for sym in sorted(os.listdir(KDIR)):
    df=load(sym)
    if df is None: continue
    df['R72']=(df['close'].shift(-72)/df['close']-1)*100
    frames.append(df)
all_df=pd.concat(frames).sort_index()
ts=all_df.groupby(all_df.index)
all_df['vol_total']=ts['volume'].transform('sum')
all_df['oi_total']=ts['sum_open_interest'].transform('sum')
all_df['oi_share']=all_df['sum_open_interest']/all_df['oi_total']
all_df['d_oi_7d']=all_df.groupby('sym')['oi_share'].diff(168)
ts_count=ts.size()
all_df=all_df[all_df.index.isin(ts_count[ts_count>=10].index)]
dc=all_df.dropna(subset=['d_oi_7d','R72']).copy()
dc['oi_rank']=dc.groupby(dc.index)['d_oi_7d'].rank(pct=True)
dc['oi_q']=pd.qcut(dc['oi_rank'],5,labels=['Q1','Q2','Q3','Q4','Q5'])
dc['year']=dc.index.year
dc['month']=dc.index.month

# ================================================================
# 1. Symbol coverage per year
# ================================================================
print("\n"+"="*70)
print("1. SYMBOL COVERAGE PER YEAR")
print("="*70)
for yr in [2024,2025,2026]:
    sub=dc[dc['year']==yr]
    nsym=sub['sym'].nunique()
    print(f"  {yr}: {nsym} symbol unik (dari 39 total), rows={len(sub)}")

# Symbols present in each year
syms_2024=set(dc[dc['year']==2024]['sym'].unique())
syms_2025=set(dc[dc['year']==2025]['sym'].unique())
syms_2026=set(dc[dc['year']==2026]['sym'].unique())
print(f"\n  2024∩2025∩2026 bilater: {len(syms_2024 & syms_2025 & syms_2026)} symbol")
only2024=syms_2024-syms_2025-syms_2026
print(f"  Symbol HANYA di 2024 (drop): {sorted(only2024) if only2024 else 'none'}")
new2026=syms_2026-syms_2025-syms_2024
print(f"  Symbol baru di 2026: {sorted(new2026) if new2026 else 'none'}")

# ================================================================
# 2. Quintile balance per year
# ================================================================
print("\n"+"="*70)
print("2. QUINTILE SIZE BALANCE PER YEAR")
print("="*70)
for yr in [2024,2025,2026]:
    sub=dc[dc['year']==yr]
    sizes=[len(sub[sub['oi_q']==q]) for q in ['Q1','Q2','Q3','Q4','Q5']]
    print(f"  {yr}: Q1={sizes[0]} Q2={sizes[1]} Q3={sizes[2]} Q4={sizes[3]} Q5={sizes[4]}")

# ================================================================
# 3. Per-year, per-symbol Q1 vs Q5 (yang drive reversal 2024?)
# ================================================================
print("\n"+"="*70)
print("3. PER-SYMBOL Q5-Q1 SPREAD PER YEAR (R72)")
print("="*70)
for yr in [2024,2025,2026]:
    sub=dc[dc['year']==yr]
    print(f"\n  --- {yr} ---")
    sym_spreads={}
    for sym in sub['sym'].unique():
        ss=sub[sub['sym']==sym]
        if len(ss)<1000: continue
        q5=ss[ss['oi_q']=='Q5']['R72'].mean()
        q1=ss[ss['oi_q']=='Q1']['R72'].mean()
        if not np.isnan(q5) and not np.isnan(q1):
            sym_spreads[sym]=q5-q1
    if sym_spreads:
        pos=[s for s in sym_spreads.values() if s>0]
        neg=[s for s in sym_spreads.values() if s<0]
        print(f"  Positive (Q5>Q1): {len(pos)}/{len(sym_spreads)}")
        print(f"  Mean spread: {np.mean(list(sym_spreads.values())):+.4f}%")
        if yr==2024 and neg and not pos:
            print(f"  >>> 2024: SEMUA symbol negative spread → reversi konsisten, BUKAN outlier")
        elif yr==2024:
            print(f"  >>> 2024: CAMPURAN pos/neg — perlu lihat distribusi")

# ================================================================
# 4. Independence check — R72 overlap
# ================================================================
print("\n"+"="*70)
print("4. R72 OVERLAP / INDEPENDENCE CHECK")
print("="*70)
# R72 = return over next 72 bars. Non-overlapping sample: every 72nd bar.
dc_nonoverlap=dc.iloc[::72]  # crude non-overlap
def spread(sub):
    if len(sub)==0: return None
    q5=sub[sub['oi_q']=='Q5']['R72'].mean()
    q1=sub[sub['oi_q']=='Q1']['R72'].mean()
    if np.isnan(q5) or np.isnan(q1): return None
    return q5-q1
print(f"  Total rows: {len(dc)}, non-overlap sample (every 72nd): {len(dc_nonoverlap)}")
for yr in [2024,2025,2026]:
    sub=dc_nonoverlap[dc_nonoverlap['year']==yr]
    s=spread(sub)
    print(f"  {yr} non-overlap: spread={s:+.4f}% (n={len(sub)})" if s is not None else f"  {yr}: insufficient")

# ================================================================
# 5. Market regime 2024 (BTC price level)
# ================================================================
print("\n"+"="*70)
print("5. BTC PRICE REGIME")
print("="*70)
btc=pd.read_parquet(os.path.join(KDIR,'BTCUSDT','klines_1h.parquet'))[['close']]
btc.index=pd.to_datetime(btc.index,utc=True)
btc['year']=btc.index.year
for yr in [2024,2025,2026]:
    sub=btc[btc['year']==yr]
    print(f"  {yr}: BTC close mean=${sub['close'].mean():,.0f}, min=${sub['close'].min():,.0f}, max=${sub['close'].max():,.0f}")

# ================================================================
# CONCLUSION
# ================================================================
print("\n"+"="*70)
print("6. DIAGNOSTIC CONCLUSION")
print("="*70)
print("  (Lihat angka di atas — saya sintesis setelah ini)")

# save
report={'study':'STUDY-008C-DIAGNOSTIC','status':'diag'}
with open(os.path.join(OUT,'STUDY-008C_DIAGNOSTIC.json'),'w') as f:
    json.dump(report,f,indent=2,default=str)
print("  Saved: research/STUDY-008C_DIAGNOSTIC.json")
print("="*70)
