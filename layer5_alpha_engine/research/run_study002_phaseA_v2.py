#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-002-FUNDING-OI-PHASE-A (VECTORIZED) - Phenomenon Discovery
Balanced & fast: vectorized pandas untuk forward returns + percentile.
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
print("STUDY-002-FUNDING-OI-PHASE-A (vectorized) - EXPLORATORY/NON-ALPHA")
print("="*70)

symbols=sorted(os.listdir(DATA_DIR))
frames=[]
for symbol in symbols:
    df=load_symbol(symbol)
    if df is None: continue
    c=df['close']
    # forward returns
    out=pd.DataFrame(index=df.index)
    for h in [1,3,6,12,24]:
        out[f'R{h}']=(c.shift(-h)/c-1)*100
    out['symbol']=symbol
    out['close']=c
    out['oi_raw']=df['sum_open_interest']
    out['funding_raw']=df['funding_rate']
    out['volume']=df['volume']
    # features
    out['oi_change_pct']=df['sum_open_interest'].pct_change()*100
    out['price_return_1']=c.pct_change()*100
    # ts z-scores rolling 100
    out['funding_ts_z']=(df['funding_rate']-df['funding_rate'].rolling(100).mean())/df['funding_rate'].rolling(100).std()
    out['oi_ts_z']=(df['sum_open_interest']-df['sum_open_interest'].rolling(100).mean())/df['sum_open_interest'].rolling(100).std()
    out['vol_ts_z']=(df['volume']-df['volume'].rolling(100).mean())/df['volume'].rolling(100).std()
    # drop last 24 rows (no forward)
    frames.append(out.iloc[:-24])

all_df=pd.concat(frames)
print(f"TOTAL rows (39 sym, forward 24bar): {len(all_df)}")

# Cross-sectional percentile per symbol (vectorized via rank)
all_df['funding_cs_pct']=all_df.groupby('symbol')['funding_raw'].rank(pct=True)
all_df['oi_cs_pct']=all_df.groupby('symbol')['oi_raw'].rank(pct=True)

print(f"Funding available: {all_df['funding_raw'].notna().mean()*100:.1f}%")
print(f"OI available: {all_df['oi_raw'].notna().mean()*100:.1f}%")

# Drop rows without funding/OI for state analysis
df_clean=all_df.dropna(subset=['funding_cs_pct','oi_cs_pct','R1','R24'])
df_clean=df_clean.dropna(subset=['R6'])
print(f"Rows lengkap (state analysis): {len(df_clean)}")

# === STATE DEFINITION ===
def price_state(s):
    return np.where(s>0.001,'UP',np.where(s<-0.001,'DOWN','FLAT'))
df_clean['PS']=price_state(df_clean['price_return_1'])
df_clean['OI_S']=pd.cut(df_clean['oi_cs_pct'],bins=[0,0.33,0.66,1.0],labels=['OI_LOW','OI_MID','OI_HIGH'],include_lowest=True)
df_clean['FD_S']=pd.cut(df_clean['funding_cs_pct'],bins=[0,0.33,0.66,1.0],labels=['FUND_LOW','FUND_MID','FUND_HIGH'],include_lowest=True)

def group_stats(g):
    return {'n':len(g),'R1':round(g['R1'].mean(),4),'R3':round(g['R3'].mean(),4),
            'R6':round(g['R6'].mean(),4),'R12':round(g['R12'].mean(),4),'R24':round(g['R24'].mean(),4)}

# ============ 2-3 DISTRIBUTION ============
print("\n"+"="*70)
print("2-3. DISTRIBUTION")
print("="*70)
fr=df_clean['funding_raw'].dropna()
oic=df_clean['oi_change_pct'].dropna()
print(f"Funding raw: mean={fr.mean():.6f} P5={fr.quantile(.05):.6f} P50={fr.median():.6f} P95={fr.quantile(.95):.6f}")
print(f"OI change%: mean={oic.mean():.4f} P5={oic.quantile(.05):.4f} P50={oic.median():.4f} P95={oic.quantile(.95):.4f}")

# ============ 6 PRICE×OI ============
print("\n"+"="*70)
print("6. PRICE × OI (E[R1],E[R6],E[R24])")
print("="*70)
print(f"  {'Price':<6}{'OI':<9}{'n':>6}{'E[R1]':>9}{'E[R6]':>9}{'E[R24]':>9}")
for ps in ['UP','DOWN']:
    for oi_s in ['OI_LOW','OI_MID','OI_HIGH']:
        sub=df_clean[(df_clean['PS']==ps)&(df_clean['OI_S']==oi_s)]
        if len(sub)<20: continue
        print(f"  {ps:<6}{oi_s:<9}{len(sub):>6}{sub['R1'].mean():>+9.3f}{sub['R6'].mean():>+9.3f}{sub['R24'].mean():>+9.3f}")

# ============ 7 FUNDING×OI ============
print("\n"+"="*70)
print("7. FUNDING × OI (E[R1],E[R6],E[R24])")
print("="*70)
print(f"  {'Funding':<10}{'OI':<9}{'n':>6}{'E[R1]':>9}{'E[R6]':>9}{'E[R24]':>9}")
for fd_s in ['FUND_LOW','FUND_MID','FUND_HIGH']:
    for oi_s in ['OI_LOW','OI_MID','OI_HIGH']:
        sub=df_clean[(df_clean['FD_S']==fd_s)&(df_clean['OI_S']==oi_s)]
        if len(sub)<20: continue
        print(f"  {fd_s:<10}{oi_s:<9}{len(sub):>6}{sub['R1'].mean():>+9.3f}{sub['R6'].mean():>+9.3f}{sub['R24'].mean():>+9.3f}")

# ============ 8 FUNDING×OI×PRICE (3D) ============
print("\n"+"="*70)
print("8. FUNDING × OI × PRICE (E[R1],E[R6],E[R24])")
print("="*70)
print(f"  {'Funding':<9}{'OI':<8}{'Pr':<5}{'n':>6}{'E[R1]':>9}{'E[R6]':>9}{'E[R24]':>9}")
print("  "+"-"*58)
table=[]
for fd_s in ['FUND_LOW','FUND_MID','FUND_HIGH']:
    for oi_s in ['OI_LOW','OI_MID','OI_HIGH']:
        for ps in ['UP','DOWN']:
            sub=df_clean[(df_clean['FD_S']==fd_s)&(df_clean['OI_S']==oi_s)&(df_clean['PS']==ps)]
            if len(sub)<20: continue
            e1=sub['R1'].mean();e6=sub['R6'].mean();e24=sub['R24'].mean()
            print(f"  {fd_s:<9}{oi_s:<8}{ps:<5}{len(sub):>6}{e1:>+9.3f}{e6:>+9.3f}{e24:>+9.3f}")
            table.append({'funding':fd_s,'oi':oi_s,'price':ps,'n':int(len(sub)),
                          'E_R1':round(float(e1),4),'E_R3':round(float(sub['R3'].mean()),4),
                          'E_R6':round(float(e6),4),'E_R12':round(float(sub['R12'].mean()),4),
                          'E_R24':round(float(e24),4)})

# ============ 9-10 HORIZON DECAY (state ekstrem) ============
print("\n"+"="*70)
print("9-10. FORWARD SURFACE + HORIZON DECAY (state ekstrem)")
print("="*70)
extreme_states=[('FUND_HIGH','OI_HIGH','UP'),('FUND_HIGH','OI_HIGH','DOWN'),
                ('FUND_HIGH','OI_LOW','UP'),('FUND_LOW','OI_LOW','DOWN'),
                ('FUND_LOW','OI_HIGH','UP'),('FUND_LOW','OI_LOW','UP')]
for (fd_s,oi_s,ps) in extreme_states:
    sub=df_clean[(df_clean['FD_S']==fd_s)&(df_clean['OI_S']==oi_s)&(df_clean['PS']==ps)]
    if len(sub)<20: continue
    dec=[round(sub[f'R{h}'].mean(),4) for h in [1,3,6,12,24]]
    print(f"  {fd_s}+{oi_s}+{ps} (n={len(sub)}): R1={dec[0]:+.3f} R3={dec[1]:+.3f} R6={dec[2]:+.3f} R12={dec[3]:+.3f} R24={dec[4]:+.3f}")

# ============ 11 CROSS-SYMBOL CONSISTENCY ============
print("\n"+"="*70)
print("11. CROSS-SYMBOL CONSISTENCY (FUND_HIGH+OI_HIGH+UP on R6)")
print("="*70)
key=('FUND_HIGH','OI_HIGH','UP')
sym_res=[]
for sym in symbols:
    sub=df_clean[(df_clean['symbol']==sym)&(df_clean['FD_S']=='FUND_HIGH')&(df_clean['OI_S']=='OI_HIGH')&(df_clean['PS']=='UP')]
    if len(sub)>=10:
        e6=sub['R6'].mean();sym_res.append((sym,int(len(sub)),e6))
        print(f"  {sym}: n={len(sub)}, E[R6]={e6:+.3f}%")
n_pos=sum(1 for _,_,e in sym_res if e>0)
print(f"  {n_pos}/{len(sym_res)} symbol positif pada state ini")

# ============ 12 LONG/SHORT ASYMMETRY ============
print("\n"+"="*70)
print("12. LONG/SHORT ASYMMETRY (setelah Price UP vs DOWN)")
print("="*70)
up=df_clean[df_clean['PS']=='UP'];down=df_clean[df_clean['PS']=='DOWN']
print(f"  Setelah UP : R1={up['R1'].mean():+.4f} R6={up['R6'].mean():+.4f} R24={up['R24'].mean():+.4f} (n={len(up)})")
print(f"  Setelah DOWN: R1={down['R1'].mean():+.4f} R6={down['R6'].mean():+.4f} R24={down['R24'].mean():+.4f} (n={len(down)})")

# ============ 14 NEGATIVE FINDINGS helper ============
# Mencari state yang jelas-jelas flat (no edge) - untuk menuang negative findings
print("\n"+"="*70)
print("REFERENSI: baseline E[R] keseluruhan")
print("="*70)
print(f"  All: R1={df_clean['R1'].mean():+.4f} R6={df_clean['R6'].mean():+.4f} R24={df_clean['R24'].mean():+.4f} (n={len(df_clean)})")

report={
    'study':'STUDY-002-FUNDING-OI-PHASE-A','status':'EXPLORATORY/NON-ALPHA','parent':'STUDY-002',
    'goal':'Phenomenon discovery - BUKAN strategy search',
    'guardrails':['no threshold selection','no TP/SL opt','no train/val/test state selection',
                  'no MTC on descriptive states','label=observed phenomenon unregistered'],
    'n_symbols':len(symbols),'n_rows':len(all_df),'n_tagged':int(len(df_clean)),
    'distributions':{'funding_raw':{'mean':round(float(fr.mean()),7),'P5':round(float(fr.quantile(.05)),7),
        'P50':round(float(fr.median()),7),'P95':round(float(fr.quantile(.95)),7)},
        'oi_change_pct':{'mean':round(float(oic.mean()),4),'P5':round(float(oic.quantile(.05)),4),
        'P50':round(float(oic.median()),4),'P95':round(float(oic.quantile(.95)),4)},
        'missing':{'oi_avail_pct':round(float(all_df['oi_raw'].notna().mean()*100),1),
                   'funding_avail_pct':round(float(all_df['funding_raw'].notna().mean()*100),1)}},
    'states_3d':table,'n_explorations':len(table),
    'baseline_all':{'R1':round(float(df_clean['R1'].mean()),4),'R6':round(float(df_clean['R6'].mean()),4),
                    'R24':round(float(df_clean['R24'].mean()),4)},
    'note':'Fenomena menonjol = OBSERVED - unregistered. Belum pre-registered.',
    'candidate_for_phase_b':[],'negative_findings':[],
}
with open(os.path.join(RESEARCH_DIR,'STUDY-002_FUNDING_OI_PHASE_A.json'),'w') as f:
    json.dump(report,f,indent=2,default=str)
print("\nSaved to research/STUDY-002_FUNDING_OI_PHASE_A.json")
print("="*70)
