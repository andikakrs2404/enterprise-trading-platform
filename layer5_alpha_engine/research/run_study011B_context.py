#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-011B — CONTEXT ENGINE VALIDATION
========================================
Bukan studi alpha. Bukan market structure.
Preregistered (ex-ante, narrow):

  H1: Breadth memperkuat RS spread konsisten di 2024/2025/2026?
      (High breadth > Low breadth di SETIAP tahun)
  H2: Breadth juga memperkuat ΔOI_share_7d spread? (R72)
      (cross-check feature independen — anti multiple-testing illusion)
  H3: Interaction effect survive TRAIN/VAL/TEST per symbol?
  H4: Economic viability net 8/12/16 bps untuk conditional strategy

Endpoints (dikunci, bukan post-hoc):
  Price RS → R24 (primary STUDY-006/011)
  ΔOI_share_7d → R72 (primary STUDY-008, frozen)
  Breadth HIGH = top 20% breadth timestamps (breadth_q == Q5)
  Breadth LOW  = sisanya (Q1-Q4)

Framework rule: temporal evidence pakai NON-OVERLAP sample
(step=horizon: 24 utk R24, 72 utk R72).
"""
import json, os
import pandas as pd, numpy as np

DATA='/home/rtk/Bot-Multi-Edge-metrics/data'
KDIR=DATA+'/klines'; MDIR=DATA+'/metrics'
OUT='/home/rtk/enterprise-trading-platform/layer5_alpha_engine/research'

Q5='Q5'; Q1='Q1'

def load(sym):
    k=os.path.join(KDIR,sym,'klines_1h.parquet')
    m=os.path.join(MDIR,sym,'metrics_1h.parquet')
    if not os.path.exists(k): return None
    df=pd.read_parquet(k)[['close']].copy()
    df=df.rename_axis('ts').reset_index()
    df['ts']=pd.to_datetime(df['ts'],utc=True)
    df['ret']=df['close'].pct_change()
    df['ret24']=df['close'].pct_change(24)
    df['above_ma20']=(df['close']>df['close'].rolling(480).mean()).astype(float)
    df['R24']=(df['close'].shift(-24)/df['close']-1)*100
    df['R72']=(df['close'].shift(-72)/df['close']-1)*100
    if os.path.exists(m):
        met=pd.read_parquet(m); met=met.rename_axis('ts').reset_index()
        met['ts']=pd.to_datetime(met['ts'],utc=True)
        df=df.merge(met[['ts','sum_open_interest']],on='ts',how='left')
    else: df['sum_open_interest']=np.nan
    df['sym']=sym
    return df

print("="*70)
print("STUDY-011B — CONTEXT ENGINE VALIDATION (breadth × feature activation)")
print("H1 RS×breadth per-year | H2 OI_share×breadth | H3 TRAIN/VAL/TEST | H4 net")
print("="*70)

frames=[]
for sym in sorted(os.listdir(KDIR)):
    df=load(sym)
    if df is not None: frames.append(df)
all_df=pd.concat(frames,ignore_index=True)
all_df=all_df.sort_values(['sym','ts']).reset_index(drop=True)
ts_count=all_df.groupby('ts').size()
valid=ts_count[ts_count>=10].index
all_df=all_df[all_df['ts'].isin(valid)].copy()
all_df['year']=all_df['ts'].dt.year

# ---- OI share & d_oi_7d (STUDY-008 frozen definition) ----
all_df['oi_total']=all_df.groupby('ts')['sum_open_interest'].transform('sum')
all_df['oi_share']=all_df['sum_open_interest']/all_df['oi_total']
all_df['d_oi_7d']=all_df.groupby('sym')['oi_share'].diff(168)

# ---- Breadth market state (exclude BTC/ETH) ----
ALT=[s for s in all_df['sym'].unique() if s not in ('BTCUSDT','ETHUSDT')]
bdf=(all_df[all_df['sym'].isin(ALT)]
     .groupby('ts')['above_ma20'].mean().rename('alt_breadth').reset_index()
     .sort_values('ts'))
bdf['breadth_q']=pd.qcut(bdf['alt_breadth'],5,labels=['Q1','Q2','Q3','Q4','Q5'],duplicates='drop')
bdf['breadth_high']=(bdf['breadth_q']==Q5).astype(int)
all_df=all_df.merge(bdf[['ts','alt_breadth','breadth_q','breadth_high']],on='ts',how='left')

# ---- Cross-sectional ranks ----
all_df['rs_rank']=all_df.groupby('ts')['ret24'].rank(pct=True)
all_df['rs_q']=pd.qcut(all_df['rs_rank'],5,labels=['R1','R2','R3','R4','R5'],duplicates='drop')
all_df['oi_rank']=all_df.groupby('ts')['d_oi_7d'].rank(pct=True)
all_df['oi_q']=pd.qcut(all_df['oi_rank'],5,labels=['Q1','Q2','Q3','Q4','Q5'],duplicates='drop')

# ---- Non-overlap samples ----
all_df['seq']=all_df.groupby('sym').cumcount()
dc24=all_df[all_df['seq']%24==0].copy()   # non-overlap utk R24 (RS)
dc72=all_df[all_df['seq']%72==0].copy()   # non-overlap utk R72 (OI_share)
print(f"Rows: full={len(all_df)} non-overlap R24={len(dc24)} R72={len(dc72)}")

def spread(df, qcol, qhi, qlo, target):
    hi=df[df[qcol]==qhi][target].mean()
    lo=df[df[qcol]==qlo][target].mean()
    return (hi-lo, hi, lo, ((df[qcol]==qhi)|(df[qcol]==qlo)).sum())

# ================================================================
# H1: RS spread by breadth state, per year (non-overlap R24)
# ================================================================
print("\n"+"="*70)
print("H1: RS spread (R5-R1, R24) — breadth HIGH (Q5) vs LOW (Q1-Q4)")
print("="*70)
agg={}
for yr in [2024,2025,2026]:
    sub=dc24[dc24['year']==yr]
    row={}
    for bh,name in [(1,'HIGH'),(0,'LOW')]:
        s=sub[sub['breadth_high']==bh]
        sp,hi,lo,n=spread(s,'rs_q','R5','R1','R24')
        row[name]=(sp,n)
        print(f"  {yr} breadth {name:>4}: RS spread={sp:+.4f}% (n={n})")
    agg[yr]=row
    ok = row['HIGH'][0] > row['LOW'][0]
    print(f"  → {yr}: {'HIGH>LOW ✅' if ok else 'HIGH<=LOW ❌'}")
# aggregate
for bh,name in [(1,'HIGH'),(0,'LOW')]:
    s=dc24[dc24['breadth_high']==bh]
    sp,hi,lo,n=spread(s,'rs_q','R5','R1','R24')
    print(f"  ALL breadth {name:>4}: RS spread={sp:+.4f}% (n={n})")
h1_all_ok = all(agg[y]['HIGH'][0] > agg[y]['LOW'][0] for y in agg)
print(f"  H1 verdict: {'PASS ✅ semua tahun HIGH>LOW' if h1_all_ok else 'FAIL ❌ tidak semua tahun'}")

# ================================================================
# H2: OI_share_7d spread by breadth state, per year (non-overlap R72)
# ================================================================
print("\n"+"="*70)
print("H2: ΔOI_share_7d spread (Q5-Q1, R72) — breadth HIGH vs LOW")
print("="*70)
agg2={}
for yr in [2024,2025,2026]:
    sub=dc72[dc72['year']==yr]
    row={}
    for bh,name in [(1,'HIGH'),(0,'LOW')]:
        s=sub[sub['breadth_high']==bh]
        sp,hi,lo,n=spread(s,'oi_q','Q5','Q1','R72')
        row[name]=(sp,n)
        print(f"  {yr} breadth {name:>4}: OI spread={sp:+.4f}% (n={n})")
    agg2[yr]=row
    ok = row['HIGH'][0] > row['LOW'][0]
    print(f"  → {yr}: {'HIGH>LOW ✅' if ok else 'HIGH<=LOW ❌'}")
for bh,name in [(1,'HIGH'),(0,'LOW')]:
    s=dc72[dc72['breadth_high']==bh]
    sp,hi,lo,n=spread(s,'oi_q','Q5','Q1','R72')
    print(f"  ALL breadth {name:>4}: OI spread={sp:+.4f}% (n={n})")
h2_all_ok = all(agg2[y]['HIGH'][0] > agg2[y]['LOW'][0] for y in agg2)
print(f"  H2 verdict: {'PASS ✅ semua tahun HIGH>LOW' if h2_all_ok else 'FAIL ❌ tidak semua tahun'}")

# ================================================================
# H3: TRAIN/VAL/TEST per symbol (60/20/20) utk interaction
# ================================================================
print("\n"+"="*70)
print("H3: Interaction (spread HIGH - spread LOW) per TRAIN/VAL/TEST")
print("="*70)
def assign_split(df):
    df=df.copy()
    df['split']=''
    for sym in df['sym'].unique():
        idx=df[df['sym']==sym].index; n=len(idx)
        df.loc[idx[:int(n*0.6)],'split']='train'
        df.loc[idx[int(n*0.6):int(n*0.8)],'split']='val'
        df.loc[idx[int(n*0.8):],'split']='test'
    return df

dc24s=assign_split(dc24)
dc72s=assign_split(dc72)
print("\n  --- RS (R24) interaction ---")
deltas_rs={}
for sp_ in ['train','val','test']:
    sub=dc24s[dc24s['split']==sp_]
    sh=spread(sub[sub['breadth_high']==1],'rs_q','R5','R1','R24')[0]
    sl=spread(sub[sub['breadth_high']==0],'rs_q','R5','R1','R24')[0]
    deltas_rs[sp_]=(sh,sl,sh-sl)
    print(f"  {sp_:>5}: HIGH={sh:+.4f}% LOW={sl:+.4f}% Δ={sh-sl:+.4f}%")
print("\n  --- ΔOI_share_7d (R72) interaction ---")
deltas_oi={}
for sp_ in ['train','val','test']:
    sub=dc72s[dc72s['split']==sp_]
    sh=spread(sub[sub['breadth_high']==1],'oi_q','Q5','Q1','R72')[0]
    sl=spread(sub[sub['breadth_high']==0],'oi_q','Q5','Q1','R72')[0]
    deltas_oi[sp_]=(sh,sl,sh-sl)
    print(f"  {sp_:>5}: HIGH={sh:+.4f}% LOW={sl:+.4f}% Δ={sh-sl:+.4f}%")

# ================================================================
# H4: Economic viability — conditional strategy net 8/12/16 bps
# ================================================================
print("\n"+"="*70)
print("H4: Net after cost — RS long/short, unconditional vs breadth-conditional")
print("="*70)
# Using non-overlap dc24 TEST split
test=dc24s[dc24s['split']=='test']
g_uncond=spread(test,'rs_q','R5','R1','R24')[0]
test_hi=test[test['breadth_high']==1]
g_cond=spread(test_hi,'rs_q','R5','R1','R24')[0]
print(f"  TEST — unconditional RS: gross={g_uncond:+.4f}% (n trades≈{len(test)}/2)")
print(f"  TEST — breadth-HIGH only: gross={g_cond:+.4f}% (n trades≈{len(test_hi)}/2)")
print(f"  Coverage breadth HIGH di TEST: {len(test_hi)/len(test)*100:.0f}% timestamps")
for fee in [8,12,16]:
    net_u=g_uncond-fee*2/100
    net_c=g_cond-fee*2/100
    print(f"  Fee {fee:>2}bps:  uncond net={net_u:+.4f}% ({net_u*100:+.1f}bps) | "
          f"cond high net={net_c:+.4f}% ({net_c*100:+.1f}bps) "
          f"{'✅' if net_c>0 else '❌'}")
# OI_share conditional net (R72, TEST)
print()
test72=dc72s[dc72s['split']=='test']
g_oi_u=spread(test72,'oi_q','Q5','Q1','R72')[0]
g_oi_c=spread(test72[test72['breadth_high']==1],'oi_q','Q5','Q1','R72')[0]
print(f"  TEST — OI_share unconditional: gross={g_oi_u:+.4f}% | breadth-HIGH: {g_oi_c:+.4f}%")
for fee in [8,12,16]:
    net_c=g_oi_c-fee*2/100
    print(f"  Fee {fee:>2}bps: cond OI net={net_c:+.4f}% ({net_c*100:+.1f}bps) {'✅' if net_c>0 else '❌'}")

# ================================================================
# SUMMARY
# ================================================================
print("\n"+"="*70)
print("SUMMARY")
print("="*70)
print(f"H1 (RS × breadth, per-tahun):  {'PASS' if h1_all_ok else 'FAIL'}")
print(f"H2 (OI_share × breadth, per-tahun): {'PASS' if h2_all_ok else 'FAIL'}")
rs_deltas=[deltas_rs[s][2] for s in ['train','val','test']]
oi_deltas=[deltas_oi[s][2] for s in ['train','val','test']]
rs_cons=all(np.sign(d)==np.sign(rs_deltas[0]) for d in rs_deltas if abs(d)>1e-8)
oi_cons=all(np.sign(d)==np.sign(oi_deltas[0]) for d in oi_deltas if abs(d)>1e-8)
print(f"H3a (RS interaction TRAIN/VAL/TEST): {'CONSISTENT' if rs_cons else 'INCONSISTENT'} {rs_deltas}")
print(f"H3b (OI interaction TRAIN/VAL/TEST): {'CONSISTENT' if oi_cons else 'INCONSISTENT'} {oi_deltas}")

report={
 'study':'STUDY-011B-CONTEXT-ENGINE','preregistered':True,
 'H1_RS_per_year':{str(y):{'HIGH':round(agg[y]['HIGH'][0],5),'LOW':round(agg[y]['LOW'][0],5)} for y in agg},
 'H2_OI_per_year':{str(y):{'HIGH':round(agg2[y]['HIGH'][0],5),'LOW':round(agg2[y]['LOW'][0],5)} for y in agg2},
 'H3_RS_delta':{s:round(deltas_rs[s][2],5) for s in ['train','val','test']},
 'H3_OI_delta':{s:round(deltas_oi[s][2],5) for s in ['train','val','test']},
 'H1_pass':h1_all_ok,'H2_pass':h2_all_ok,
 'H3_RS_consistent':rs_cons,'H3_OI_consistent':oi_cons}
with open(os.path.join(OUT,'STUDY-011B_CONTEXT_ENGINE.json'),'w') as f:
    json.dump(report,f,indent=2,default=str)
print(f"\nSaved: research/STUDY-011B_CONTEXT_ENGINE.json")
print("="*70)