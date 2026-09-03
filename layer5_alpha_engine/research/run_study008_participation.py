#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-008 — RELATIVE PARTICIPATION (OI Share + Volume Share)
Phase A: Phenomenon Discovery (NON-ALPHA)
============================================================
Pertanyaan riset:
Apakah perubahan pangsa partisipasi antar aset mengandung
informasi prediktif yang TIDAK ditangkap oleh price momentum?

Framing: RELATIVE, bukan ABSOLUTE.
Bukan "OI tinggi bullish", tapi "aset yang mengambil pangsa dari universe".

GUARDRAIL:
- Phase A: deskriptif, no threshold, no optimization
- Quintile analysis, monotonicity, horizon, symbol breadth
- Persistence check
- Correlation OI_share vs VOL_share
- Label: Observed Phenomenon (Unregistered)
"""
import json, os, random, statistics
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
print("STUDY-008 — RELATIVE PARTICIPATION (Phase A)")
print("Pertanyaan: Apakah pangsa partisipasi relatif → forward return?")
print("Bukan: OI tinggi = bullish. Tapi: Δshare informatif?")
print("="*70)

syms=sorted(os.listdir(KDIR))
frames=[]
for sym in syms:
    df=load(sym)
    if df is None: continue
    # Forward returns
    for h in [6,12,24,48,72]:
        df[f'R{h}']=(df['close'].shift(-h)/df['close']-1)*100
    # Price momentum (24h return) — untuk kontrol
    df['ret24']=df['close'].pct_change(24)
    frames.append(df)

all_df=pd.concat(frames).sort_index()
print(f"Rows: {len(all_df)}, symbols: {len(syms)}")

# Hanya timestamp dengan OI tersedia (minimal 10 symbol)
ts_oicount=all_df.groupby(all_df.index)['sum_open_interest'].apply(lambda x: x.notna().sum())
valid_ts=ts_oicount[ts_oicount>=10].index
all_df=all_df[all_df.index.isin(valid_ts)]
print(f"Rows with >=10 OI symbols: {len(all_df)}")

# ================================================================
# COMPUTE RELATIVE PARTICIPATION SHARES
# ================================================================
ts=all_df.groupby(all_df.index)
all_df['vol_total']=ts['volume'].transform('sum')
all_df['oi_total']=ts['sum_open_interest'].transform('sum')
all_df['vol_share']=all_df['volume']/all_df['vol_total']
all_df['oi_share']=all_df['sum_open_interest']/all_df['oi_total']

# Change over 1d, 3d, 7d (per symbol)
for col,base in [('oi_share','oi_share'),('vol_share','vol_share')]:
    for days in [1,3,7]:
        bars=days*24
        all_df[f'd {col}_{days}d']=all_df.groupby('sym')[col].diff(bars)
        # Rank change cross-sectionally
        all_df[f'd {col}_{days}d_rank']=ts[f'd {col}_{days}d'].rank(pct=True)

# Cross-sectional return spread for dispersion
disp=ts['ret24'].agg(lambda x: x.quantile(0.9)-x.quantile(0.1))
disp_med=disp.median()
all_df['disp_state']=all_df.index.map(disp-disp_med>0).map({True:'HIGH',False:'LOW'})

# Dropna
need_cols=[f'd {c}_{d}d' for c in ['oi_share','vol_share'] for d in [1,3,7]]+ \
           [f'R{h}' for h in [6,12,24,48,72]]+['ret24']
dc=all_df.dropna(subset=need_cols).copy()
print(f"Clean rows: {len(dc)}")

# ================================================================
# QUINTILE ANALYSIS — ΔOI_share_1d → Forward Return
# ================================================================
print("\n"+"="*70)
print("1. QUINTILE: ΔOI_share (1-day change) → Forward Return")
print("="*70)
dc['q']=pd.qcut(dc['d oi_share_1d_rank'],5,labels=['Q1_loss','Q2','Q3','Q4','Q5_gain'])
print(f"  {'quintile':<12}{'n':>8}{'R6':>10}{'R12':>10}{'R24':>10}{'R48':>10}{'R72':>10}{'%pos24':>8}")
for q in ['Q1_loss','Q2','Q3','Q4','Q5_gain']:
    g=dc[dc['q']==q]
    pos24=(g['R24']>0).mean()*100
    print(f"  {q:<12}{len(g):>8}{g['R6'].mean():>+10.4f}{g['R12'].mean():>+10.4f}"
          f"{g['R24'].mean():>+10.4f}{g['R48'].mean():>+10.4f}{g['R72'].mean():>+10.4f}{pos24:>8.0f}%")
# Monotonicity
means=[dc[dc['q']==q]['R24'].mean() for q in ['Q1_loss','Q2','Q3','Q4','Q5_gain']]
mono=sum(1 for i in range(len(means)-1) if means[i]<=means[i+1])
spread_q=means[-1]-means[0]
print(f"  Spread(Q5-Q1) R24: {spread_q:+.4f}%, Monotonic: {mono}/4")
dc.drop('q',axis=1,inplace=True)

# ================================================================
# QUINTILE — ΔOI_share 3d & 7d (persistence check)
# ================================================================
for days in [3,7]:
    print(f"\n  --- ΔOI_share {days}d → R24 ---")
    dc['q']=pd.qcut(dc[f'd oi_share_{days}d_rank'],5,labels=['Q1','Q2','Q3','Q4','Q5'])
    for q in ['Q1','Q2','Q3','Q4','Q5']:
        g=dc[dc['q']==q]
        print(f"  {q}: n={len(g):>7}, R24={g['R24'].mean():>+.4f}%, "
              f"R48={g['R48'].mean():>+.4f}%")
    means=[dc[dc['q']==q]['R24'].mean() for q in ['Q1','Q2','Q3','Q4','Q5']]
    mono=sum(1 for i in range(len(means)-1) if means[i]<=means[i+1])
    print(f"  Spread: {means[-1]-means[0]:+.4f}%, Mono: {mono}/4")
    dc.drop('q',axis=1,inplace=True)

# ================================================================
# QUINTILE — ΔVOL_share 1d, 3d, 7d
# ================================================================
print("\n"+"="*70)
print("2. QUINTILE: ΔVOL_share → Forward Return")
print("="*70)
for days in [1,3,7]:
    print(f"\n  --- ΔVOL_share {days}d ---")
    dc['q']=pd.qcut(dc[f'd vol_share_{days}d_rank'],5,labels=['Q1','Q2','Q3','Q4','Q5'])
    for q in ['Q1','Q2','Q3','Q4','Q5']:
        g=dc[dc['q']==q]
        print(f"  {q}: n={len(g):>7}, R24={g['R24'].mean():>+.4f}%, "
              f"R48={g['R48'].mean():>+.4f}%")
    means=[dc[dc['q']==q]['R24'].mean() for q in ['Q1','Q2','Q3','Q4','Q5']]
    mono=sum(1 for i in range(len(means)-1) if means[i]<=means[i+1])
    print(f"  Spread: {means[-1]-means[0]:+.4f}%, Mono: {mono}/4")
    dc.drop('q',axis=1,inplace=True)

# ================================================================
# 3. CORRELATION OI_share vs VOL_share (are they redundant?)
# ================================================================
print("\n"+"="*70)
print("3. CORRELATION: ΔOI_share vs ΔVOL_share")
print("="*70)
for days in [1,3,7]:
    cols=[f'd oi_share_{days}d',f'd vol_share_{days}d']
    valid=dc[cols].dropna()
    corr=valid[cols[0]].corr(valid[cols[1]])
    print(f"  Δ{days}d: corr={corr:.3f} "
          f"({'REDUNDANT' if abs(corr)>0.7 else 'OVERLAP' if abs(corr)>0.4 else 'DISTINCT'})")

# ================================================================
# 4. MONOTONICITY ACROSS HORIZONS (ΔOI_share_1d)
# ================================================================
print("\n"+"="*70)
print("4. HORIZON MONOTONICITY: ΔOI_share_1d → Q5 spread per horizon")
print("="*70)
dc['q']=pd.qcut(dc['d oi_share_1d_rank'],5,labels=['Q1','Q2','Q3','Q4','Q5'])
print(f"  {'horizon':<8}{'Q1':>10}{'Q5':>10}{'spread':>10}{'%pos_Q5':>10}")
for h in ['R6','R12','R24','R48','R72']:
    q1=dc[dc['q']=='Q1'][h].mean()
    q5=dc[dc['q']=='Q5'][h].mean()
    s=q5-q1
    pos5=(dc[dc['q']=='Q5'][h]>0).mean()*100
    print(f"  {h:<8}{q1:>+10.4f}{q5:>+10.4f}{s:>+10.4f}{pos5:>10.0f}%")
dc.drop('q',axis=1,inplace=True)

# ================================================================
# 5. SYMBOL BREADTH (ΔOI_share_1d)
# ================================================================
print("\n"+"="*70)
print("5. SYMBOL BREADTH: % symbol Q5>Q1 per R24")
print("="*70)
dc['q']=pd.qcut(dc['d oi_share_1d_rank'],5,labels=['Q1','Q2','Q3','Q4','Q5'])
sym_q5=dc[dc['q']=='Q5'].groupby('sym')['R24'].mean()
sym_q1=dc[dc['q']=='Q1'].groupby('sym')['R24'].mean()
common=sym_q5.index.intersection(sym_q1.index)
pos=(sym_q5[common]>sym_q1[common]).sum()
print(f"  {pos}/{len(common)} symbols (Q5 > Q1): {pos/len(common)*100:.0f}%")
dc.drop('q',axis=1,inplace=True)

# ================================================================
# 6. DISPERSION CONDITIONAL (HIGH vs LOW)
# ================================================================
print("\n"+"="*70)
print("6. DISPERSION CONDITIONAL: ΔOI_share_1d in HIGH vs LOW dispersion")
print("="*70)
dc['q']=pd.qcut(dc['d oi_share_1d_rank'],5,labels=['Q1','Q2','Q3','Q4','Q5'])
for disp_s in ['HIGH','LOW']:
    sub=dc[dc['disp_state']==disp_s]
    spread_vals=[]
    for q in ['Q1','Q5']:
        g=sub[sub['q']==q]
        spread_vals.append(g['R24'].mean() if len(g)>0 else 0)
    print(f"  {disp_s} dispersion: Q1={spread_vals[0]:+.4f}%, Q5={spread_vals[1]:+.4f}%, "
          f"spread={spread_vals[1]-spread_vals[0]:+.4f}% (n={len(sub)})")
dc.drop('q',axis=1,inplace=True)

# ================================================================
# 7. NEGATIVE FINDINGS
# ================================================================
print("\n"+"="*70)
print("7. NEGATIVE FINDINGS")
print("="*70)
print("  1. OI data tersedia untuk ~39 simbol, tapi coverage bervariasi per timestamp")
print("  2. Δshare bisa noisy karena total universe berubah (sym enter/exit)")
print("  3. Correlation ΔOI vs ΔVOL perlu dicek — mungkin redundant")
print("  4. Regime interaction belum diuji (temporal split)")
print("  5. Sector/classification belum diterapkan")

# ================================================================
# SAVE
# ================================================================
report={
    'study':'STUDY-008-RELATIVE-PARTICIPATION-PHASE-A','status':'EXPLORATORY/NON-ALPHA',
    'n_symbols':len(syms),'n_rows':len(dc),
    'features_tested':[f'd oi_share_{d}d' for d in [1,3,7]]+[f'd vol_share_{d}d' for d in [1,3,7]],
    'horizons':[6,12,24,48,72],
    'dispersion_test':True,
    'label':'Observed Phenomenon (Unregistered)'}
with open(os.path.join(OUT,'STUDY-008_PARTICIPATION_PHASE_A.json'),'w') as f:
    json.dump(report,f,indent=2,default=str)
print("\nSaved: research/STUDY-008_PARTICIPATION_PHASE_A.json")
print("STUDY-008 Phase A SELESAI")
print("="*70)
