#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-009 — Volatility Regime Change (Cross-Sectional) - Phase A/B validation
=============================================================================
PREREGISTERED (dikunci ex-ante di STUDY-009_PREREGISTRATION.md):
  Vol change = σ_6h / σ_168h, rank per timestamp (tidak ada threshold optimasi)
  Horizon: R24 / R48 / R72 (preregistered — tidak pilih terbaik setelah hasil)
  Discovery: full sample. Temporal: non-overlap ATAU HAC.
  Temporal split per symbol 60/20/20.
  Double-sort: vs Price RS, vs dispersion.
  Net after 8/12/16 bps.
  Failure criteria ex-ante.

Discipline: report Q1 & Q5 SEPARATELY, not just spread.
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
print("STUDY-009 — VOLATILITY REGIME CHANGE (cross-sectional)")
print("σ_6h/σ_168h ratio, rank per ts. Pre-registered. Failure criteria frozen.")
print("="*70)

frames=[]
for sym in sorted(os.listdir(KDIR)):
    df=load(sym)
    if df is None: continue
    df['ret']=df['close'].pct_change()
    df['sigma_s']=df['ret'].rolling(6).std()   # 6h
    df['sigma_b']=df['ret'].rolling(168).std() # 7d
    df['vratio']=df['sigma_s']/df['sigma_b']
    df['ret24']=df['close'].pct_change(24)
    df['oi_share']=None
    df['d_oi_7d']=None
    for h in [24,48,72]:
        df[f'R{h}']=(df['close'].shift(-h)/df['close']-1)*100
    frames.append(df)

all_df=pd.concat(frames).sort_index()
ts=all_df.groupby(all_df.index)
# OI share (for double-sort vs ΔOI_share)
all_df['oi_total_x']=ts['sum_open_interest'].transform('sum')
all_df['oi_share']=all_df['sum_open_interest']/all_df['oi_total_x']
all_df['d_oi_7d']=all_df.groupby('sym')['oi_share'].diff(168)
# Price RS
all_df['rs_rank']=ts['ret24'].rank(pct=True)
# Market dispersion
disp=ts['ret24'].agg(lambda x: x.quantile(0.9)-x.quantile(0.1))
disp_med=disp.median()
all_df['disp_state']=all_df.index.map(lambda x: 'HIGH' if disp.get(x,0)>disp_med else 'LOW')

# filter >=10 sym
ts_count=ts.size()
all_df=all_df[all_df.index.isin(ts_count[ts_count>=10].index)]
need=['vratio','ret24','rs_rank','R24','R48','R72','d_oi_7d']
dc=all_df.dropna(subset=need).copy()
# vol change rank per timestamp
dc['vol_rank']=dc.groupby(dc.index)['vratio'].rank(pct=True)
dc['vol_q']=pd.qcut(dc['vol_rank'],5,labels=['Q1','Q2','Q3','Q4','Q5'])
dc['year']=dc.index.year
print(f"Clean rows: {len(dc)}, sym: {len(dc['sym'].unique())}")

# ================================================================
# 1. QUINTILE — individual Q1..Q5 per horizon (full sample, discovery)
# ================================================================
print("\n"+"="*70)
print("1. QUINTILE (full sample, discovery) — vol change → fwd return")
print("="*70)
hors=['R24','R48','R72']
print(f"  {'Q':>5}",end='')
for h in hors: print(f"{h:>10}",end='')
print(f"{'%pos24':>8}")
for q in ['Q1','Q2','Q3','Q4','Q5']:
    g=dc[dc['vol_q']==q]
    row=f"  {q:>5}"
    for h in hors: row+=f"{g[h].mean():>+10.4f}"
    row+=f"{(g['R24']>0).mean()*100:>7.0f}%"
    print(row)
# spread
def spread(sub,h='R24'):
    q5=sub[sub['vol_q']=='Q5'][h].mean()
    q1=sub[sub['vol_q']=='Q1'][h].mean()
    return q5-q1,q5,q1
print("\n  Spread (Q5-Q1):")
for h in hors:
    s,q5,q1=spread(dc,h)
    print(f"  {h}: Q5={q5:+.4f}% Q1={q1:+.4f}% Spread={s:+.4f}%")

# ================================================================
# 2. TEMPORAL SPLIT (per symbol, 60/20/20)
# ================================================================
print("\n"+"="*70)
print("2. TEMPORAL SPLIT per symbol (60/20/20) — directional consistency")
print("="*70)
dc['split']=''
for sym in dc['sym'].unique():
    idx=dc[dc['sym']==sym].index
    n=len(idx)
    dc.loc[idx[:int(n*0.6)],'split']='train'
    dc.loc[idx[int(n*0.6):int(n*0.8)],'split']='val'
    dc.loc[idx[int(n*0.8):],'split']='test'
for h in hors:
    print(f"\n  --- {h} ---")
    print(f"  {'split':>6}{'Q1':>10}{'Q5':>10}{'spread':>10}{'breadth':>10}")
    dirs=[]
    for s in ['train','val','test']:
        sub=dc[dc['split']==s]
        sp,q5,q1=spread(sub,h)
        # breadth
        sym_q5=sub[sub['vol_q']=='Q5'].groupby('sym')[h].mean()
        sym_q1=sub[sub['vol_q']=='Q1'].groupby('sym')[h].mean()
        common=sym_q5.index.intersection(sym_q1.index)
        pos=(sym_q5[common]>sym_q1[common]).sum()/len(common)*100 if len(common)>0 else 0
        dirs.append(sp)
        print(f"  {s:>6}{q1:>+10.4f}{q5:>+10.4f}{sp:>+10.4f}{pos:>9.0f}%")
    signs=set(np.sign([d for d in dirs if d is not None]))
    nz=[d for d in dirs if d is not None and abs(d)>1e-6]
    consistent = (len(set(np.sign(nz)))<=1) if nz else False
    print(f"  → Direction sign across splits: {['+','-'][0] if consistent else 'MIXED'} {'CONSISTENT ✅' if consistent and nz else 'INCONSISTENT ❌'}")

# ================================================================
# 3. NON-OVERLAP temporal evidence (critical per STUDY-008 rule)
# ================================================================
print("\n"+"="*70)
print("3. NON-OVERLAP SAMPLE (temporal evidence, per STUDY-008 rule)")
print("="*70)
# Non-overlap for R72: take every 72nd row per symbol
dc_no=dc.groupby('sym',group_keys=False).apply(lambda g: g.iloc[::72]).reset_index(drop=True)
print(f"  Non-overlap (R72) sample: {len(dc_no)}")
print(f"  {'split':>6}{'Q1':>10}{'Q5':>10}{'spread':>10}{'n':>8}")
dirs_no=[]
for s in ['train','val','test']:
    sub=dc_no[dc_no['split']==s]
    if len(sub)<500: 
        print(f"  {s:>6}  (insufficient n={len(sub)})"); continue
    sp,q5,q1=spread(sub,'R72')
    dirs_no.append(sp)
    print(f"  {s:>6}{q1:>+10.4f}{q5:>+10.4f}{sp:>+10.4f}{len(sub):>8}")
nz=[d for d in dirs_no if d is not None and abs(d)>1e-6]
consistent_no = (len(set(np.sign(nz)))<=1) if nz else False
print(f"  → Non-overlap direction: {'CONSISTENT ✅' if consistent_no and nz else 'INCONSISTENT/INSUFFICIENT ❌'}")

# ================================================================
# 4. DOUBLE-SORT vs Price RS (independence)
# ================================================================
print("\n"+"="*70)
print("4. DOUBLE-SORT: vol change × Price RS → R24 (independence check)")
print("="*70)
dc['rs_q']=pd.qcut(dc['rs_rank'],5,labels=['RS1','RS2','RS3','RS4','RS5'])
mat=np.zeros((5,5))
for i,qv in enumerate(['Q1','Q2','Q3','Q4','Q5']):
    for j,qr in enumerate(['RS1','RS2','RS3','RS4','RS5']):
        m=(dc['vol_q']==qv)&(dc['rs_q']==qr)
        mat[i,j]=dc.loc[m,'R24'].mean() if m.sum()>0 else np.nan
print(f"  {'':>8}{'RS1':>8}{'RS2':>8}{'RS3':>8}{'RS4':>8}{'RS5':>8}")
for i,qv in enumerate(['Q1','Q2','Q3','Q4','Q5']):
    print(f"  VOL:{qv:<3}{mat[i,0]:>+8.4f}{mat[i,1]:>+8.4f}{mat[i,2]:>+8.4f}{mat[i,3]:>+8.4f}{mat[i,4]:>+8.4f}")
marg_vol=mat.mean(axis=1)
marg_rs=mat.mean(axis=0)
print(f"\n  Marginal VOL: Q1={marg_vol[0]:+.4f} Q5={marg_vol[4]:+.4f} spread={marg_vol[4]-marg_vol[0]:+.4f}")
print(f"  Marginal RS:  RS1={marg_rs[0]:+.4f} RS5={marg_rs[4]:+.4f} spread={marg_rs[4]-marg_rs[0]:+.4f}")
cond_rs3=mat[4,2]-mat[0,2]  # VOL spread conditional on neutral RS
print(f"  VOL spread conditional on RS3 (neutral): {cond_rs3:+.4f}%")
print(f"  → {'INDEPENDENT ✅' if cond_rs3>0 else 'MOMENTUM PROXY ❌'}")

# ================================================================
# 5. REGIME interaction (LOW vs HIGH dispersion)
# ================================================================
print("\n"+"="*70)
print("5. REGIME INTERACTION — LOW vs HIGH dispersion (vol change → R24)")
print("="*70)
for ds in ['LOW','HIGH']:
    sub=dc[dc['disp_state']==ds]
    sp,q5,q1=spread(sub,'R24')
    print(f"  {ds} dispersion: Q1={q1:+.4f}% Q5={q5:+.4f}% spread={sp:+.4f}% (n={len(sub)})")

# ================================================================
# 6. NET AFTER COST (8/12/16 bps) — TEST window
# ================================================================
print("\n"+"="*70)
print("6. NET AFTER COST (TEST window, R24)")
print("="*70)
test=dc[dc['split']=='test']
gross=spread(test,'R24')[0]
print(f"  Gross spread (TEST): {gross:+.4f}%")
for fee in [8,12,16]:
    net=gross-fee*2/100
    print(f"  Fee {fee:>2}bps: net={net:+.4f}% ({net*100:+.1f}bps) → {'POSITIVE ✅' if net>0 else 'NEGATIVE ❌'}")

# ================================================================
# VERDICT per pre-registered failure criteria
# ================================================================
print("\n"+"="*70)
print("VERDICT (per pre-registered criteria)")
print("="*70)
verdict={'study':'STUDY-009','status':'ANALYSIS COMPLETE'}
with open(os.path.join(OUT,'STUDY-009_VOLREGIME.json'),'w') as f:
    json.dump(verdict,f,indent=2,default=str)
print("  Saved: research/STUDY-009_VOLREGIME.json")
print("  (Saya sintesis verdict berdasarkan output di atas.)")
print("="*70)
