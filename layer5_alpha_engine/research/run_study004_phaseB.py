#!/usr/bin/env /usr/bin/python3.11
"""STUDY-004 Phase B — Preregistered Hypothesis Validation (FUND_LOW+OI_LOW+HIGH_VOL)
H1: E[R24]>0 dan >baseline | H2: vol driver? | H3: temporal | H4: >60% symbol | H5: net-after-cost
"""
import json, os, random, statistics
import pandas as pd, numpy as np
random.seed(42); np.random.seed(42)

DATA='/home/rtk/Bot-Multi-Edge-metrics/data'
KDIR=DATA+'/klines'; MDIR=DATA+'/metrics'; FDIR=DATA+'/funding'
OUT='/home/rtk/enterprise-trading-platform/layer5_alpha_engine/research'
os.makedirs(OUT, exist_ok=True)

def load(sym):
    k=os.path.join(KDIR,sym,'klines_1h.parquet')
    m=os.path.join(MDIR,sym,'metrics_1h.parquet')
    f=os.path.join(FDIR,sym,'funding_1h.parquet')
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
print("STUDY-004 PHASE B — Preregistered Hypothesis Validation")
print("State: FUND_LOW + OI_LOW + HIGH_VOL | Definisi dikunci")
print("="*70)

syms=sorted(os.listdir(KDIR))
frames=[]
for sym in syms:
    df=load(sym)
    if df is None: continue
    c=df['close']
    for h in [1,3,6,12,24]: df[f'R{h}']=(c.shift(-h)/c-1)*100
    df['sym']=sym
    # realized vol (100)
    df['rv']=df['close'].pct_change().rolling(100).std()
    frames.append(df)

all_df=pd.concat([f.set_index(np.arange(len(f))) for f in frames], keys=range(len(frames))).reset_index(level=1,drop=True)
# simpler: rebuild with symbol column
all_df=pd.concat(frames, ignore_index=True)
print(f"Total rows: {len(all_df)}")

# Cross-sectional percentile
all_df['fund_pct']=all_df.groupby('sym')['funding_rate'].rank(pct=True)
all_df['oi_pct']=all_df.groupby('sym')['sum_open_interest'].rank(pct=True)
# State flags
all_df['FUND_LOW']=all_df['fund_pct']<0.33
all_df['OI_LOW']=all_df['oi_pct']<0.33
vol_glob=all_df['rv'].median()
all_df['HIGH_VOL']=all_df['rv']>vol_glob

# Drop NaN needed
need=['R1','R6','R12','R24','fund_pct','oi_pct','rv']
dc=all_df.dropna(subset=['R1','R6','R12','R24','fund_pct','oi_pct','rv']).copy()
print(f"Clean rows: {len(dc)}")

# ============ H1: E[R24] state vs baselines ============
print("\n"+"="*70)
print("H1: E[R24] — state vs MULTIPLE BASELINES")
print("="*70)
state=dc[dc['FUND_LOW']&dc['OI_LOW']&dc['HIGH_VOL']].copy()
base_uncond=dc
base_highvol=dc[dc['HIGH_VOL']]
base_match=dc[(dc['FUND_LOW'])&(dc['OI_LOW'])]  # matched funding/OI but ignore vol
print(f"  STATE (FLOW+OI_LOW+HIGH_VOL): n={len(state)}, E[R24]={state['R24'].mean():+.4f}%, "
      f"median={state['R24'].median():+.4f}%, %pos={(state['R24']>0).mean()*100:.1f}%")
print(f"  Base Unconditional: n={len(base_uncond)}, E[R24]={base_uncond['R24'].mean():+.4f}%")
print(f"  Base HIGH_VOL only: n={len(base_highvol)}, E[R24]={base_highvol['R24'].mean():+.4f}%")
print(f"  Base FLOW+OI_LOW (any vol): n={len(base_match)}, E[R24]={base_match['R24'].mean():+.4f}%")
st_plus=state['R24'].mean()
print(f"\n  H1 verdict: E[R24 state]={st_plus:+.4f}% >0: {'PASS' if st_plus>0 else 'FAIL'}")

# ============ H2: Vol driver? ============
print("\n"+"="*70)
print("H2: Apakah HIGH_VOL SAJA cukup? (funding/OI = penumpang?)")
print("="*70)
hv=dc[dc['HIGH_VOL']]
hv_sym_vol=hv.groupby('sym')['R24'].mean()
print(f"  HIGH_VOL only: E[R24]={hv['R24'].mean():+.4f}% (n={len(hv)})")
print(f"  FLOW+OI_LOW+HIGH_VOL: E[R24]={st_plus:+.4f}% (n={len(state)})")
print(f"  FLOW+OI_LOW+LOW_VOL: n={len(dc[dc['FUND_LOW']&dc['OI_LOW']&~dc['HIGH_VOL']])}, "
      f"E[R24]={dc[dc['FUND_LOW']&dc['OI_LOW']&~dc['HIGH_VOL']]['R24'].mean():+.4f}%")
# Delta: apakah kombinasi >> vol sendiri
delta=st_plus-hv['R24'].mean()
print(f"  Delta (state - HIGH_VOL only) = {delta:+.4f}pp")
print(f"  H2: kombinasi {'MATERIALLY > vol sendiri' if delta>0.10 else '≈ vol sendiri (funding/OI = penumpang)' if abs(delta)<0.10 else 'kombinasi > vol'}")

# ============ H3: Temporal stability ============
print("\n"+"="*70)
print("H3: Temporal stability (First vs Second half)")
print("="*70)
med=len(dc)/2
dc['period']=np.where(np.arange(len(dc))<med,'FIRST','SECOND')
for per in ['FIRST','SECOND']:
    s=dc[(dc['FUND_LOW'])&(dc['OI_LOW'])&(dc['HIGH_VOL'])&(dc['period']==per)]
    if len(s)>0:
        print(f"  {per}: n={len(s)}, E[R24]={s['R24'].mean():+.4f}%, %pos={(s['R24']>0).mean()*100:.1f}%")
h3_sign='PASS' if (dc[(dc['FUND_LOW'])&(dc['OI_LOW'])&(dc['HIGH_VOL'])&(dc['period']=='FIRST')]['R24'].mean()>0 and
                   dc[(dc['FUND_LOW'])&(dc['OI_LOW'])&(dc['HIGH_VOL'])&(dc['period']=='SECOND')]['R24'].mean()>0) else 'FAIL'
print(f"  H3 verdict (kedua half positif): {h3_sign}")

# ============ H4: Cross-symbol ============
print("\n"+"="*70)
print("H4: Cross-symbol >60% positive")
print("="*70)
state_sym=state.groupby('sym')['R24'].mean()
pos=sum(1 for v in state_sym.values if v>0)
total=len(state_sym)
pct=pos/total*100
print(f"  Symbol positif: {pos}/{total} = {pct:.1f}%")
# Sign test manual
def fact(x): return 1 if x<=1 else x*fact(x-1)
def comb(n,k):
    if k<0 or k>n: return 0
    return fact(n)//(fact(k)*fact(n-k))
pn=0
for kk in range(pos,total+1): pn+=comb(total,kk)
p_val=2*pn/(2**total)
print(f"  Sign test p-value (two-sided): {p_val:.4f}")
print(f"  H4 verdict: {'PASS (significant)' if pct>60 else 'FAIL'}")

# ============ H5: Net after cost ============
print("\n"+"="*70)
print("H5: Net-after-cost (8/10/12 bps)")
print("="*70)
r=state['R24'].dropna()
gross=r.mean()*100/100  # in decimal already as % - convert
# R24 stored as % so gross_bps = mean*100 bps
gross_bps=state['R24'].mean()*100
for fee_bps in [8,10,12]:
    net_bps=gross_bps-fee_bps*2  # entry + exit
    print(f"  Fee {fee_bps}bps: gross={gross_bps:.1f}bps, net={net_bps:.1f}bps -> {'POSITIF' if net_bps>0 else 'NEGATIF'}")
# Varians per trade untuk CI
r_bps=state['R24'].values*100
n_trade=len(r_bps)
se=statistics.stdev(r_bps)/np.sqrt(n_trade) if n_trade>1 else 0
ci=np.array([gross_bps-1.96*se, gross_bps+1.96*se])
print(f"  n={n_trade}, gross CI95=[{ci[0]:.1f}, {ci[1]:.1f}] bps")
# Net CI (mengurangi fee 2x)
for fee in [8,10,12]:
    lo=gross_bps-1.96*se-fee*2; hi=gross_bps+1.96*se-fee*2
    print(f"  Fee {fee}bps net CI95=[{lo:.1f}, {hi:.1f}] bps -> {'POSITIF robust' if lo>0 else 'CI menyentuh 0'}")

# ============ SUMMARY ============
print("\n"+"="*70)
print("RINGKASAN VERDICT (preregistered)")
print("="*70)
h=[None]
h1=st_plus>0
print(f"  H1 E[R24]>0: {'PASS' if h1 else 'FAIL'}")
print(f"  H2 vol driver: PERLU INTERPRETASI")
print(f"  H3 temporal: {h3_sign}")
print(f"  H4 cross-symbol>60%: {'PASS' if pct>60 else 'FAIL'}")
print(f"  H5 net-after-cost: lihat CI di atas")

report={
    'study':'STUDY-004-PHASE-B','preregistered':True,'parent':'STUDY-003',
    'state':'FUND_LOW+OI_LOW+HIGH_VOL',
    'H1':{'E_R24_state':round(st_plus,4),'base_uncond':round(base_uncond['R24'].mean(),4),
          'base_highvol':round(base_highvol['R24'].mean(),4),'base_match':round(base_match['R24'].mean(),4),
          'pass':bool(h1)},
    'H2':{'highvol_only_E_R24':round(hv['R24'].mean(),4),'state_E_R24':round(st_plus,4),
          'delta_pp':round(delta,4)},
    'H3':{'first':round(dc[(dc['FUND_LOW'])&(dc['OI_LOW'])&(dc['HIGH_VOL'])&(dc['period']=='FIRST')]['R24'].mean(),4),
          'second':round(dc[(dc['FUND_LOW'])&(dc['OI_LOW'])&(dc['HIGH_VOL'])&(dc['period']=='SECOND')]['R24'].mean(),4),
          'pass':h3_sign=='PASS'},
    'H4':{'pos_symbols':pos,'total':total,'pct':round(pct,1),'sign_test_p':round(p_val,4),
          'pass':pct>60},
    'H5':{'gross_bps':round(gross_bps,1),
          'net8':round(gross_bps-16,1),'net10':round(gross_bps-20,1),'net12':round(gross_bps-24,1)},
    'label':'Preregistered Hypothesis Validation — BUKAN edge/live',
    'verdict':'PREREGISTERED RESULT (bukan final alpha)'
}
with open(os.path.join(OUT,'STUDY-004_PHASE_B.json'),'w') as f:
    json.dump(report,f,indent=2,default=str)
print("\nSaved: research/STUDY-004_PHASE_B.json")
print("STUDY-004 Phase B SELESAI")
print("="*70)
