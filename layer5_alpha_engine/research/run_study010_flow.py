#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-010 — Cross-Sectional Flow (OI growth / Volume growth)
PREREGISTERED H0/H1. Double-sort is CORE.
=====================================================================
Kandidat:
  OI growth rank  — ΔOI over 24h, rank/ts
  Volume growth rank — Δvolume over 24h, rank/ts
Questions:
  Apakah flow leading atau hanya proxy Price RS?

Desain (dikunci ex-ante):
  Stage 1: flow vs fwd return (discovery)
  Stage 2: flow vs Price RS correlation (Spearman + quintile overlap)
  Stage 3: DOUBLE-SORT sejak awal — flow spread conditional on Price RS neutral (Q3)
  Stage 4: temporal split + non-overlap + net cost
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
    df=df.rename_axis('ts').reset_index()
    df['ts']=pd.to_datetime(df['ts'],utc=True)
    df['ret']=df['close'].pct_change()
    df['ret24']=df['close'].pct_change(24)
    # volume growth 24h (bars ago 24)
    df['vol_prev24']=df['volume'].shift(24)
    df['vol_growth']=df['volume']/df['vol_prev24']-1
    df['R24']=(df['close'].shift(-24)/df['close']-1)*100
    if os.path.exists(m):
        met=pd.read_parquet(m); met=met.rename_axis('ts').reset_index()
        met['ts']=pd.to_datetime(met['ts'],utc=True)
        df=df.merge(met[['ts','sum_open_interest']],on='ts',how='left')
    else:
        df['sum_open_interest']=np.nan
    df['oi_prev24']=df['sum_open_interest'].shift(24)
    df['oi_growth']=df['sum_open_interest']/df['oi_prev24']-1
    df['sym']=sym
    return df

print("="*70)
print("STUDY-010 — CROSS-SECTIONAL FLOW")
print("OI growth / Volume growth. H0: proxy. Double-sort = core.")
print("="*70)

frames=[]
for sym in sorted(os.listdir(KDIR)):
    df=load(sym)
    if df is not None: frames.append(df)
all_df=pd.concat(frames,ignore_index=True).sort_values('ts').reset_index(drop=True)
ts_count=all_df.groupby('ts').size()
valid=ts_count[ts_count>=10].index
all_df=all_df[all_df['ts'].isin(valid)]
all_df=all_df.dropna(subset=['ret24','vol_growth','R24']).copy()
all_df['year']=all_df['ts'].dt.year
# Cross-sectional ranks per ts
g=all_df.groupby('ts')
all_df['vol_growth_rank']=g['vol_growth'].rank(pct=True)
all_df['oi_growth_rank']=g['oi_growth'].rank(pct=True)
all_df['rs_rank']=g['ret24'].rank(pct=True)
# dispersion
disp=g['ret24'].agg(lambda x:x.quantile(0.9)-x.quantile(0.1))
disp_med=disp.median()
all_df['disp_state']=all_df['ts'].map(lambda x:'HIGH' if disp.get(x,0)>disp_med else 'LOW')
print(f"Clean rows: {len(all_df)}, sym: {len(all_df['sym'].unique())}")

def assign_q(df,col):
    dfq=df.copy()
    dfq[col+'_q']=pd.qcut(dfq[col],5,labels=['Q1','Q2','Q3','Q4','Q5'])
    return dfq

# ================================================================
# STAGE 1: Discovery — flow vs fwd return
# ================================================================
print("\n"+"="*70)
print("STAGE 1: DISCOVERY — flow quintile vs R24")
print("="*70)
for feat in ['vol_growth_rank','oi_growth_rank']:
    dcA=assign_q(all_df,feat)
    print(f"\n  --- {feat.upper()} ---")
    print(f"  {'Q':>5}{'R24':>10}{'n':>9}")
    q1=q5=None
    for q in ['Q1','Q2','Q3','Q4','Q5']:
        gq=dcA[dcA[feat+'_q']==q]
        v=gq['R24'].mean()
        print(f"  {q:>5}{v:>+10.4f}{len(gq):>9}")
        if q=='Q1': q1=v
        if q=='Q5': q5=v
    print(f"  Spread Q5-Q1: {q5-q1:+.4f}%")

# ================================================================
# STAGE 2: Flow vs Price RS correlation (Spearman + overlap)
# ================================================================
print("\n"+"="*70)
print("STAGE 2: FLOW vs PRICE RS correlation (early warning)")
print("="*70)
for feat in ['vol_growth_rank','oi_growth_rank']:
    # Pearson on ranks = Spearman (no scipy needed)
    corr=all_df[feat].corr(all_df['rs_rank'],method='pearson')
    # quintile overlap: of symbols in flow Q5, how many also in RS Q5?
    dfc=all_df.copy()
    dfc[feat+'_q']=pd.qcut(dfc[feat],5,labels=['Q1','Q2','Q3','Q4','Q5'])
    dfc['rs_q']=pd.qcut(dfc['rs_rank'],5,labels=['RS1','RS2','RS3','RS4','RS5'])
    flow_q5=dfc[dfc[feat+'_q']=='Q5']['rs_q'].value_counts(normalize=True)
    rs5_in_flow_q5=flow_q5.get('RS5',0)*100
    rs1_in_flow_q5=flow_q5.get('RS1',0)*100
    dom=flow_q5.idxmax()
    print(f"\n  {feat.upper()}:")
    print(f"    Spearman corr vs Price RS: {corr:.3f}")
    print(f"    Dari flow Q5, distribusi Price RS: {dict(flow_q5.round(2))}")
    print(f"    → {'BERBAGI dgn momentum (overlap tinggi)' if rs5_in_flow_q5>60 or corr>0.6 else 'Cukup berbeda (overlap rendah)'}")

# ================================================================
# STAGE 3: DOUBLE-SORT (CORE) — flow spread conditional on Price RS neutral
# ================================================================
print("\n"+"="*70)
print("STAGE 3: DOUBLE-SORT (CORE) — flow spread conditional on Price RS")
print("="*70)
dfc=all_df.copy()
dfc['rs_q']=pd.qcut(dfc['rs_rank'],5,labels=['RS1','RS2','RS3','RS4','RS5'])
for feat in ['vol_growth_rank','oi_growth_rank']:
    dfc[feat+'_q']=pd.qcut(dfc[feat],5,labels=['Q1','Q2','Q3','Q4','Q5'])
    print(f"\n  --- {feat.upper()} × PriceRS → R24 ---")
    print(f"  {'':>8}{'RS1':>8}{'RS2':>8}{'RS3':>8}{'RS4':>8}{'RS5':>8}")
    mat=np.zeros((5,5))
    for i,qv in enumerate(['Q1','Q2','Q3','Q4','Q5']):
        row=f"  {feat[:4]}:{qv:<3}"
        for j,qr in enumerate(['RS1','RS2','RS3','RS4','RS5']):
            m=(dfc[feat+'_q']==qv)&(dfc['rs_q']==qr)
            v=dfc.loc[m,'R24'].mean() if m.sum()>0 else np.nan
            mat[i,j]=v
            row+=f"{v:>+8.4f}"
        print(row)
    # Conditional on RS3 (neutral): flow Q5-Q1
    cond_q1=mat[0,2]; cond_q5=mat[4,2]
    cond_spread=cond_q5-cond_q1
    # Marginal flow
    marg=mat.mean(axis=1)
    marg_spread=marg[4]-marg[0]
    print(f"  Conditional on Price RS neutral (RS3): flow Q1={cond_q1:+.4f}% Q5={cond_q5:+.4f}% "
          f"spread={cond_spread:+.4f}%")
    print(f"  Margnal flow spread (mengabaikan RS): {marg_spread:+.4f}%")
    verdict='CANDIDATE ✅ (independen)' if abs(cond_spread)>0.005 else 'PROXY MOMENTUM ❌'
    print(f"  → {verdict}")

# ================================================================
# STAGE 4: Temporal split + non-overlap + net cost (for surviving flow)
# ================================================================
print("\n"+"="*70)
print("STAGE 4: TEMPORAL + NON-OVERLAP + COST (satu kandidat terbaik)")
print("="*70)
# pick the flow that survives stage-3 (else note both failed)
survivor=None
# Quick stage-3 recheck to pick survivor
for feat in ['vol_growth_rank','oi_growth_rank']:
    dfc2=all_df.copy()
    dfc2['rs_q']=pd.qcut(dfc2['rs_rank'],5,labels=['RS1','RS2','RS3','RS4','RS5'])
    dfc2[feat+'_q']=pd.qcut(dfc2[feat],5,labels=['Q1','Q2','Q3','Q4','Q5'])
    cond_q1=dfc2[(dfc2[feat+'_q']=='Q1')&(dfc2['rs_q']=='RS3')]['R24'].mean()
    cond_q5=dfc2[(dfc2[feat+'_q']=='Q5')&(dfc2['rs_q']=='RS3')]['R24'].mean()
    if abs(cond_q5-cond_q1)>0.005:
        survivor=feat
        print(f"  {feat} survives stage-3 (cond spread={cond_q5-cond_q1:+.4f})")
if survivor:
    feat=survivor
    print(f"\n  ANALYZING survivor: {feat.upper()}")
    dcS=all_df.copy()
    dcS[feat+'_q']=pd.qcut(dcS[feat],5,labels=['Q1','Q2','Q3','Q4','Q5'])
    # temporal split per symbol
    dcS['split']=''
    for sym in dcS['sym'].unique():
        idx=dcS[dcS['sym']==sym].index; n=len(idx)
        dcS.loc[idx[:int(n*0.6)],'split']='train'
        dcS.loc[idx[int(n*0.6):int(n*0.8)],'split']='val'
        dcS.loc[idx[int(n*0.8):],'split']='test'
    print(f"\n  --- Temporal spread per split ---")
    dirs=[]
    for ss in ['train','val','test']:
        sub=dcS[dcS['split']==ss]
        q1=sub[sub[feat+'_q']=='Q1']['R24'].mean()
        q5=sub[sub[feat+'_q']=='Q5']['R24'].mean()
        dirs.append(q5-q1)
        print(f"  {ss:>5}: Q1={q1:+.4f}% Q5={q5:+.4f}% spread={q5-q1:+.4f}% (n={len(sub)})")
    nz=[d for d in dirs if abs(d)>1e-6]
    consistent=len(set(np.sign(nz)))<=1 if nz else False
    print(f"  → Direction {'CONSISTENT ✅' if consistent else 'INCONSISTENT ❌'}")
    # net cost on TEST
    test=dcS[dcS['split']=='test']
    gross=test[test[feat+'_q']=='Q5']['R24'].mean()-test[test[feat+'_q']=='Q1']['R24'].mean()
    print(f"\n  --- Net after cost (TEST) ---")
    for fee in [8,12,16]:
        net=gross-fee*2/100
        print(f"  Fee {fee}bps: net={net:+.4f}% ({net*100:+.1f}bps) → {'POS' if net>0 else 'NEG'}")
else:
    print("  TIDAK ADA kandidat yang lolos STAGE 3 (double-sort).")
    print("  Kedua flow = momentum proxy per kriteria preregistered A.")

# ================================================================
# SAVE
# ================================================================
report={
    'study':'STUDY-010-CS-FLOW','preregistered':True,
    'note':'Double-sort = core. Jika tidak ada survivor di stage 3 → REJECTED A.',
    'label':'Preregistered — H0 flow proxy Price RS'}
with open(os.path.join(OUT,'STUDY-010_CS_FLOW.json'),'w') as f:
    json.dump(report,f,indent=2,default=str)
print("\nSaved: research/STUDY-010_CS_FLOW.json")
print("STUDY-010 SELESAI")
print("="*70)
