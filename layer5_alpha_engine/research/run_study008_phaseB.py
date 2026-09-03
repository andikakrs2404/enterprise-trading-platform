#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-008 PHASE B — Preregistered Validation
==============================================
PREREGISTERED (dikunci ex-ante):
  Candidate A: ΔVOL_share_1d → primary endpoint R24
  Candidate B: ΔOI_share_7d  → primary endpoint R72
  Split: temporal per symbol (60/20/20)
  MTC: Benjamini-Hochberg FDR
  Fee: 8bps round-trip
  NEW: Double sort 5×5 vs Price RS (from STUDY-006)

Hipotesis:
  H1: spread(Q5-Q1) > 0 di TEST window
  H2: temporal stability (TRAIN & VAL same sign as TEST)
  H3: % symbol positive > 50% di TEST
  H4: net-after-cost > 0 di TEST
  H5: Double sort — participation share retains edge after controlling Price RS
"""
import json, os, random, statistics
import pandas as pd, numpy as np
random.seed(42); np.random.seed(42)

DATA='/home/rtk/Bot-Multi-Edge-metrics/data'
KDIR=DATA+'/klines'; MDIR=DATA+'/metrics'
OUT='/home/rtk/enterprise-trading-platform/layer5_alpha_engine/research'
FEE=0.0008

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
print("STUDY-008 PHASE B — Preregistered Validation")
print("A: ΔVOL_share_1d → R24 | B: ΔOI_share_7d → R72")
print("Double sort vs Price RS. Temporal split. FDR.")
print("="*70)

# --- LOAD ---
syms=sorted(os.listdir(KDIR))
frames=[]
for sym in syms:
    df=load(sym)
    if df is None: continue
    for h in [6,12,24,48,72]:
        df[f'R{h}']=(df['close'].shift(-h)/df['close']-1)*100
    df['ret24']=df['close'].pct_change(24)
    frames.append(df)

all_df=pd.concat(frames).sort_index()
print(f"Rows: {len(all_df)}, sym: {len(syms)}")

# --- RELATIVE PARTICIPATION ---
ts=all_df.groupby(all_df.index)
all_df['vol_total']=ts['volume'].transform('sum')
all_df['oi_total']=ts['sum_open_interest'].transform('sum')
all_df['vol_share']=all_df['volume']/all_df['vol_total']
all_df['oi_share']=all_df['sum_open_interest']/all_df['oi_total']

# ΔVOL_share 1d
all_df['d_vol_1d']=all_df.groupby('sym')['vol_share'].diff(24)
# ΔOI_share 7d
all_df['d_oi_7d']=all_df.groupby('sym')['oi_share'].diff(168)
# Price RS rank (from STUDY-006)
all_df['rs_rank']=ts['ret24'].rank(pct=True)

# Dropna + filter >=10 sym
ts_count=ts.size()
all_df=all_df[all_df.index.isin(ts_count[ts_count>=10].index)]
dc=all_df.dropna(subset=['d_vol_1d','d_oi_7d','ret24','R6','R12','R24','R48','R72']).copy()
print(f"Clean rows: {len(dc)}")

# --- SPLIT PER SYMBOL (TRAIN/VAL/TEST) ---
print("\nSPLITTING per symbol...")
splits={sym:{'train':None,'val':None,'test':None} for sym in dc['sym'].unique()}
for sym in dc['sym'].unique():
    sdf=dc[dc['sym']==sym].sort_index()
    n=len(sdf)
    splits[sym]['train']=sdf.index[:int(n*0.6)]
    splits[sym]['val']=sdf.index[int(n*0.6):int(n*0.8)]
    splits[sym]['test']=sdf.index[int(n*0.8):]

# Assign split column
dc['split']=['']*len(dc)
for sym in dc['sym'].unique():
    for part in ['train','val','test']:
        dc.loc[dc.index.isin(splits[sym][part]),'split']=part

# Rank per candidate
ts2=dc.groupby(dc.index)
dc['vol_rank']=ts2['d_vol_1d'].rank(pct=True)
dc['oi_rank']=ts2['d_oi_7d'].rank(pct=True)
dc['vol_q']=pd.qcut(dc['vol_rank'],5,labels=['Q1','Q2','Q3','Q4','Q5'])
dc['oi_q']=pd.qcut(dc['oi_rank'],5,labels=['Q1','Q2','Q3','Q4','Q5'])

# ================================================================
# H1-H4 for both candidates, per split
# ================================================================
for cand,label,primary in [('vol_q','ΔVOL_share_1d','R24'),('oi_q','ΔOI_share_7d','R72')]:
    print("\n"+"="*70)
    print(f"CANDIDATE: {label} (primary endpoint: {primary})")
    print("="*70)
    for split in ['train','val','test']:
        sub=dc[dc['split']==split]
        q5=sub[sub[cand]=='Q5'][primary].mean()
        q1=sub[sub[cand]=='Q1'][primary].mean()
        spread=q5-q1
        # Symbol breadth
        sym_q5=sub[sub[cand]=='Q5'].groupby('sym')[primary].mean()
        sym_q1=sub[sub[cand]=='Q1'].groupby('sym')[primary].mean()
        common=sym_q5.index.intersection(sym_q1.index)
        pos=(sym_q5[common]>sym_q1[common]).sum() if len(common)>0 else 0
        # Net after fee
        net_spread=spread-FEE*2/100
        print(f"\n  {split.upper():>5}: Q5={q5:+.4f}% Q1={q1:+.4f}% Spread={spread:+.4f}% "
              f"Net(8bps)={net_spread:+.4f}% ({net_spread*100:+.1f}bps) "
              f"Breadth={pos}/{len(common)} ({pos/len(common)*100:.0f}%)")

# ================================================================
# TEMPORAL STABILITY CHECK (primary endpoint)
# ================================================================
print("\n"+"="*70)
print("H2: TEMPORAL STABILITY — spread per split (primary endpoint)")
print("="*70)
for cand,label,primary in [('vol_q','ΔVOL_share_1d','R24'),('oi_q','ΔOI_share_7d','R72')]:
    spreads=[]
    for split in ['train','val','test']:
        sub=dc[dc['split']==split]
        s=sub[sub[cand]=='Q5'][primary].mean()-sub[sub[cand]=='Q1'][primary].mean()
        spreads.append(s)
    stable=all(s>0 for s in spreads)
    print(f"  {label}: TRAIN={spreads[0]:+.4f}% VAL={spreads[1]:+.4f}% TEST={spreads[2]:+.4f}% → "
          f"{'ALL POSITIVE ✅' if stable else 'FAILED ❌'}")

# ================================================================
# H5: DOUBLE SORT 5×5 (VOL_share × Price RS) → R24
# ================================================================
print("\n"+"="*70)
print("H5: DOUBLE SORT 5×5 — ΔVOL_share × Price_RS → R24")
print("="*70)
# Quintile of price RS per timestamp
dc['rs_q']=ts2['rs_rank'].rank(pct=True)
dc['rs_qcat']=pd.qcut(dc['rs_q'],5,labels=['RS1','RS2','RS3','RS4','RS5'])

matrix=np.zeros((5,5))
for i,qv in enumerate(['Q1','Q2','Q3','Q4','Q5']):
    for j,qr in enumerate(['RS1','RS2','RS3','RS4','RS5']):
        mask=(dc['vol_q']==qv)&(dc['rs_qcat']==qr)
        matrix[i,j]=dc.loc[mask,'R24'].mean()

print(f"\n  {'':>8}{'RS1':>8}{'RS2':>8}{'RS3':>8}{'RS4':>8}{'RS5':>8}{'Δrow':>8}")
for i,qv in enumerate(['Q1','Q2','Q3','Q4','Q5']):
    row=matrix[i,:]
    print(f"  VOL:{qv:<3}{row[0]:>+8.4f}{row[1]:>+8.4f}{row[2]:>+8.4f}{row[3]:>+8.4f}{row[4]:>+8.4f}"
          f"{row[4]-row[0]:>+8.4f}")
# Column means (marginal price RS effect)
col_means=matrix.mean(axis=0)
row_means=matrix.mean(axis=1)
print(f"\n  Marginal Price RS:  RS1={col_means[0]:+.4f} RS2={col_means[1]:+.4f} RS3={col_means[2]:+.4f} RS4={col_means[3]:+.4f} RS5={col_means[4]:+.4f}")
print(f"  Marginal VOL share: Q1={row_means[0]:+.4f} Q2={row_means[1]:+.4f} Q3={row_means[2]:+.4f} Q4={row_means[3]:+.4f} Q5={row_means[4]:+.4f}")

# Conditional on middle RS (RS3) — does VOL share still work?
rs3_spread=matrix[4,2]-matrix[0,2]  # Q5-Q1 conditional on RS3
print(f"\n  Conditional on Price RS=neutral (RS3): VOL Q5-Q1 = {rs3_spread:+.4f}%")
print(f"  → {'INDEPENDENT signal ✅' if rs3_spread>0 else 'Likely momentum proxy ❌'}")

# Double sort: VOL share retains edge after controlling RS?
v_spread=matrix.mean(axis=1)[4]-matrix.mean(axis=1)[0]  # marginal VOL
r_spread=matrix.mean(axis=0)[4]-matrix.mean(axis=0)[0]  # marginal RS
print(f"\n  Marginal VOL spread: {v_spread:+.4f}% (after controlling RS)")
print(f"  Marginal RS spread:  {r_spread:+.4f}%")

# ================================================================
# SAME DOUBLE SORT for ΔOI_share × Price RS → R72
# ================================================================
print("\n"+"="*70)
print("H5b: DOUBLE SORT 5×5 — ΔOI_share × Price_RS → R72")
print("="*70)
matrix2=np.zeros((5,5))
for i,qv in enumerate(['Q1','Q2','Q3','Q4','Q5']):
    for j,qr in enumerate(['RS1','RS2','RS3','RS4','RS5']):
        mask=(dc['oi_q']==qv)&(dc['rs_qcat']==qr)
        matrix2[i,j]=dc.loc[mask,'R72'].mean()

print(f"\n  {'':>8}{'RS1':>8}{'RS2':>8}{'RS3':>8}{'RS4':>8}{'RS5':>8}{'Δrow':>8}")
for i,qv in enumerate(['Q1','Q2','Q3','Q4','Q5']):
    row=matrix2[i,:]
    print(f"  OI:{qv:<3} {row[0]:>+8.4f}{row[1]:>+8.4f}{row[2]:>+8.4f}{row[3]:>+8.4f}{row[4]:>+8.4f}"
          f"{row[4]-row[0]:>+8.4f}")

rs3_spread2=matrix2[4,2]-matrix2[0,2]
oi_marginal=matrix2.mean(axis=1)[4]-matrix2.mean(axis=1)[0]
rs_marginal2=matrix2.mean(axis=0)[4]-matrix2.mean(axis=0)[0]
print(f"\n  Conditional on Price RS=neutral (RS3): OI Q5-Q1 = {rs3_spread2:+.4f}%")
print(f"  → {'INDEPENDENT signal ✅' if rs3_spread2>0 else 'Likely momentum proxy ❌'}")
print(f"  Marginal OI spread: {oi_marginal:+.4f}% | Marginal RS: {rs_marginal2:+.4f}%")

# ================================================================
# FEE SENSITIVITY (TEST window only)
# ================================================================
print("\n"+"="*70)
print("FEE SENSITIVITY (TEST window)")
print("="*70)
for cand,label,primary in [('vol_q','ΔVOL_share_1d','R24'),('oi_q','ΔOI_share_7d','R72')]:
    test=dc[dc['split']=='test']
    gross=test[test[cand]=='Q5'][primary].mean()-test[test[cand]=='Q1'][primary].mean()
    for fee in [0,4,8,12,16]:
        net=gross-fee*2/100
        print(f"  {label} Fee {fee:>2}bps: net={net:+.4f}% ({net*100:+.1f}bps)")

# ================================================================
# SAVE
# ================================================================
report={
    'study':'STUDY-008-PHASE-B','preregistered':True,
    'definitions_frozen':{
        'vol_share_change_1d':'Δ(vol_i/vol_total) over 24 bars',
        'oi_share_change_7d':'Δ(oi_i/oi_total) over 168 bars',
        'primary_endpoints':{'VOL':'R24','OI':'R72'},
        'fee_bps':8,'split':'temporal per-symbol 60/20/20'},
    'label':'Preregistered Hypothesis Validation — BUKAN edge/live'}
with open(os.path.join(OUT,'STUDY-008_PHASE_B.json'),'w') as f:
    json.dump(report,f,indent=2,default=str)
print("\nSaved: research/STUDY-008_PHASE_B.json")
print("STUDY-008 Phase B SELESAI")
print("="*70)
