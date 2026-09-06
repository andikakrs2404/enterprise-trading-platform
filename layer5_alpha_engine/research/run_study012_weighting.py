#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-012 — WEIGHTING (Portfolio Construction, Pertanyaan 2 dari 3)
====================================================================
PREREGISTERED (STUDY-012_PREREGISTRATION.md). TANPA tuning dari hasil TEST.

5 skema (dikunci ex-ante):
  1. Equal weight            — w_i = 1/N
  2. Rank weight             — w_i ∝ 0.5 + rs_rank_i (linear)
  3. Volatility-scaled       — w_i ∝ σ_i (overweight high vol)
  4. Inverse-volatility      — w_i ∝ 1/σ_i (risk parity)
  5. Capped rank weight      — rank weight, cap 2.5×EW, renormalize

Design:
  - Long-only full universe, weights dinormalisasi per ts
  - Horizon R24, rebalance tiap 24 bar (grid non-overlap sama dgn Selection)
  - Turnover = Σ|Δw| antar rebalance; cost = turnover × fee
  - Split TRAIN/VAL/TEST 60/20/20; per-year juga dilaporkan
  - DECOMPOSITION: selection effect + weighting effect + interaction
  - Diagnostic: exposure ke Q5 winners (apakah improvement = exposure saja?)

GATE (preregistered, dari research lead):
  FAIL jika hanya TEST bagus. PASS membutuhkan:
  TRAIN>0 & VAL>0 & TEST>0 (net@12) + turnover manageable + no single-era.
"""
import json, os
import pandas as pd, numpy as np

DATA='/home/rtk/Bot-Multi-Edge-metrics/data'
KDIR=DATA+'/klines'
OUT='/home/rtk/enterprise-trading-platform/layer5_alpha_engine/research'

def load(sym):
    k=os.path.join(KDIR,sym,'klines_1h.parquet')
    if not os.path.exists(k): return None
    df=pd.read_parquet(k)[['close']].copy()
    df=df.rename_axis('ts').reset_index()
    df['ts']=pd.to_datetime(df['ts'],utc=True)
    df['ret']=df['close'].pct_change()
    df['ret24']=df['close'].pct_change(24)
    df['sigma24']=df['ret'].rolling(24).std()
    df['R24']=(df['close'].shift(-24)/df['close']-1)*100
    df['sym']=sym
    return df

print("="*70)
print("STUDY-012 — WEIGHTING (5 skema preregistered, long-only universe)")
print("="*70)

frames=[]
for sym in sorted(os.listdir(KDIR)):
    df=load(sym)
    if df is not None: frames.append(df)
all_df=pd.concat(frames,ignore_index=True).sort_values(['sym','ts']).reset_index(drop=True)
ts_count=all_df.groupby('ts').size()
valid=ts_count[ts_count>=10].index
all_df=all_df[all_df['ts'].isin(valid)].dropna(subset=['ret24','R24']).copy()

# RS rank & quintile (frozen STUDY-006)
all_df['rs_rank']=all_df.groupby('ts')['ret24'].rank(pct=True)
all_df['rs_q']=pd.cut(all_df['rs_rank'],bins=[-0.01,0.2,0.4,0.6,0.8,1.01],
                      labels=[0,1,2,3,4]).astype(float)

# ---- Non-overlap rebalance grid: ts di mana SEMUA simbol ada di seq%24==0 ----
all_df['sym_seq']=all_df.groupby('sym').cumcount()
grid_mask=all_df.groupby('ts')['sym_seq'].transform(lambda s:(s%24==0).all())
dc=all_df[grid_mask].copy().sort_values(['ts','sym'])
print(f"Grid: {dc['ts'].nunique()} rebalance periods, {dc['sym'].nunique()} sym")

# ---- WEIGHTS per scheme (per ts, normalized) ----
N_per_ts=dc.groupby('ts')['sym'].transform('count')
dc['w_ew']=1.0/N_per_ts
dc['w_rank']=(0.5+dc['rs_rank'])
dc['w_vol']=dc['sigma24'].fillna(0.01)
dc['w_invvol']=1.0/dc['sigma24'].clip(lower=1e-4)
# capped rank: cap = 2.5 × EW weight (=2.5/N), renormalize
cap=2.5/N_per_ts
wcap=np.minimum(dc['w_rank'],cap)
dc['w_capped']=wcap
# normalize semua per ts
for c in ['w_ew','w_rank','w_vol','w_invvol','w_capped']:
    dc[c]=dc[c]/dc.groupby('ts')[c].transform('sum')

# ---- Portfolio gross return per ts per scheme ----
schemes=['w_ew','w_rank','w_vol','w_invvol','w_capped']
pf=dc.groupby('ts').agg(ts=('ts','first')).reset_index(drop=True)
pf['year']=pd.to_datetime(pf['ts']).dt.year
for c in schemes:
    g=dc.groupby('ts').apply(lambda d:(d[c]*d['R24']).sum(),include_groups=False)
    pf[c]=g.values*100  # bps
# Q5-only equal weight (selection reference)
q5=dc[dc['rs_q']==4].copy()
q5['w_q5ew']=1.0/q5.groupby('ts')['sym'].transform('count')
gq5=q5.groupby('ts').apply(lambda d:(d['w_q5ew']*d['R24']).sum(),include_groups=False).reindex(pf['ts']).fillna(0)
pf['q5_ew']=gq5.values*100

# ---- Turnover per scheme (Σ|Δw| antar rebalance) ----
dc=dc.sort_values(['ts','sym'])
prev_w=dc.groupby('sym')[schemes].shift(1)
delta=(dc[schemes]-prev_w[schemes]).abs()
to=delta.groupby(dc['ts']).sum()
# first period turnover = 1.0 (full entry)
to=to.reindex(pf['ts']).fillna(1.0)
for i,c in enumerate(schemes):
    pf[c+'_to']=to[c].values
# q5_ew turnover (full turnover each rebalance: 1.0 entry + changes)
pf['q5_ew_to']=1.0  # upper bound; q5 re-selection flips ~full

# ---- Split 60/20/20 ----
pf=pf.sort_values('ts').reset_index(drop=True)
n=len(pf)
pf['split']=''
pf.loc[:int(n*0.6),'split']='train'
pf.loc[int(n*0.6):int(n*0.8),'split']='val'
pf.loc[int(n*0.8):,'split']='test'

def net_bps(pf, col, fee):
    return (pf[col]-pf[col+'_to']*fee).to_numpy()

def report_split(sub,col,fee=12,annual=True):
    g=sub[col]; to=sub[col+'_to'].mean()
    gross=g.mean(); net=g.mean()-to*fee
    sharpe=g.mean()/g.std()*np.sqrt(365) if g.std()>0 else np.nan
    hit=(g>0).mean()*100
    return {'gross':gross,'to':to,'net':net,'sharpe':sharpe,'hit':hit,'n':len(g)}

print("\n"+"="*70)
print("TABEL — per split, per skema (bps). Net = gross − turnover×fee")
print("="*70)
for c in schemes+['q5_ew']:
    name=c.replace('w_','')
    cells=[]
    for s in ['train','val','test']:
        r=report_split(pf[pf['split']==s],c)
        cells.append(f"g={r['gross']:+.1f} n12={r['net']:+.1f} to={r['to']:.2f}")
    print(f"  {name:<12} | TRAIN {cells[0]:<34} | VAL {cells[1]:<34} | TEST {cells[2]}")

# ---- GATE check ----
print("\n"+"="*70)
print("GATE (preregistered): semua split net@12>0 + turnover + no single-era")
print("="*70)
for c in schemes+['q5_ew']:
    name=c.replace('w_','')
    nets={s:report_split(pf[pf['split']==s],c)['net'] for s in ['train','val','test']}
    allpos=all(v>0 for v in nets.values())
    to=pf[c+'_to'].mean()
    # per-year net@12
    yr={}
    for y in [2024,2025,2026]:
        sub=pf[pf['year']==y]
        yr[y]=sub[c].mean()-sub[c+'_to'].mean()*12
    pos_years=sum(1 for v in yr.values() if v>0)
    print(f"  {name:<12} TRAIN={nets['train']:+.1f} VAL={nets['val']:+.1f} TEST={nets['test']:+.1f} "
          f"| all3+={'PASS' if allpos else 'FAIL'} | to={to:.2f} | "
          f"tahun+={pos_years}/3 {dict((k,round(v,1)) for k,v in yr.items())}")

# ---- DECOMPOSITION (net@12): selection + weighting + interaction ----
print("\n"+"="*70)
print("DECOMPOSITION (net@12 bps, full sample) — dari mana improvement datang?")
print("="*70)
univ_net=pf['w_ew'].mean()-pf['w_ew_to'].mean()*12
q5_net=pf['q5_ew'].mean()-pf['q5_ew_to'].mean()*12
print(f"  Baseline universe EW net@12 = {univ_net:+.1f} bps")
print(f"  Q5-only EW net@12           = {q5_net:+.1f} bps")
print(f"  SELECTION effect (Q5EW−UnivEW) = {q5_net-univ_net:+.1f} bps")
for c in schemes:
    name=c.replace('w_','')
    scheme_net=pf[c].mean()-pf[c+'_to'].mean()*12
    sel_eff=q5_net-univ_net
    weight_eff=scheme_net-q5_net          # improvement di luar Q5-EW
    port_eff=scheme_net-univ_net
    inter=port_eff-sel_eff-weight_eff
    print(f"  {name:<12} port_eff={port_eff:+.1f} | sel_eff={sel_eff:+.1f} | "
          f"weight_eff={weight_eff:+.1f} | interaction={inter:+.1f}")

# ---- EXPOSURE diagnostic: apakah improvement = eksposure ke Q5 semata? ----
print("\n"+"="*70)
print("EXPOSURE DIAGNOSTIC — berapa bobot ke Q5 members, dan return dari sana?")
print("="*70)
for c in schemes:
    name=c.replace('w_','')
    dc['is_q5']=(dc['rs_q']==4).astype(float)
    expo=dc.groupby('ts').apply(lambda d:(d[c]*d['is_q5']).sum(),include_groups=False).reindex(pf['ts']).fillna(0)
    ret_q5=dc.groupby('ts').apply(lambda d:(d[c]*d['is_q5']*d['R24']).sum(),include_groups=False).reindex(pf['ts']).fillna(0)*100
    share=(ret_q5/(dc.groupby('ts').apply(lambda d:(d[c]*d['R24']).sum(),include_groups=False).reindex(pf['ts']).fillna(0)*100)).mean()
    print(f"  {name:<12} avg Q5 exposure={expo.mean():.2f} ({expo.mean()*100:.0f}% capital) | "
          f"% return dari Q5={share*100:.0f}%")
# EW reference
expo_ew=dc.groupby('ts').apply(lambda d:(d['w_ew']*d['is_q5']).sum(),include_groups=False).reindex(pf['ts']).fillna(0)
print(f"  {'ew':<12} avg Q5 exposure={expo_ew.mean():.2f} ({expo_ew.mean()*100:.0f}% capital) [reference]")

# ---- SAVE ----
report={'study':'STUDY-012-WEIGHTING','schemes':[c.replace('w_','') for c in schemes],
        'gates':'semua split net@12>0 + to manageable + no single-era',
        'decomposition':'selection+weighting+interaction','exposure_diag':True}
with open(os.path.join(OUT,'STUDY-012_WEIGHTING.json'),'w') as f:
    json.dump(report,f,indent=2,default=str)
print(f"\nSaved: research/STUDY-012_WEIGHTING.json")
print("="*70)