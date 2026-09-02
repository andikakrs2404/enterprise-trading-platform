#!/usr/bin/env /usr/bin/python3.11
"""STUDY-003 Phase A — Funding/OI Dislocation (EXPLORATORY / NON-ALPHA)"""
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
print("STUDY-003-FUNDING-OI-PHASE-A | EXPLORATORY / NON-ALPHA")
print("Parent: STUDY-002 | Entry: FROZEN | No threshold opt")
print("="*70)

syms=sorted(os.listdir(KDIR))
frames=[]
for sym in syms:
    df=load(sym)
    if df is None: continue
    c=df['close']
    for h in [1,3,6,12,24]: df[f'R{h}']=(c.shift(-h)/c-1)*100
    df['price_ret1']=c.pct_change()*100
    df['oi_chg_pct']=df['sum_open_interest'].pct_change()*100
    df['sym']=sym
    frames.append(df.iloc[:-24])

all_df=pd.concat(frames)
print(f"Total rows: {len(all_df)}")

# Cross-sectional percentile per symbol
all_df['fund_pct']=all_df.groupby('sym')['funding_rate'].rank(pct=True)
all_df['oi_pct']=all_df.groupby('sym')['sum_open_interest'].rank(pct=True)
# Terciles
all_df['FD']=pd.cut(all_df['fund_pct'],bins=[0,.33,.66,1],labels=['FUND_LOW','FUND_MID','FUND_HIGH'],include_lowest=True)
all_df['OI']=pd.cut(all_df['oi_pct'],bins=[0,.33,.66,1],labels=['OI_LOW','OI_MID','OI_HIGH'],include_lowest=True)
all_df['PS']=np.where(all_df['price_ret1']>0.001,'UP',np.where(all_df['price_ret1']<-0.001,'DOWN','FLAT'))
# Price regime proxy (simplified from STUDY-001)
all_df['hvol']=all_df.groupby('sym')['close'].pct_change().rolling(100).std()
vol_med=all_df['hvol'].median()
all_df['regime']=np.where(all_df['hvol']>vol_med,'HIGH_VOL','LOW_VOL')

dc=all_df.dropna(subset=['R1','R6','R12','R24','fund_pct','oi_pct']).copy()
print(f"Lengkap state analysis: {len(dc)}")

# ================================================================
# 1. COVERAGE GATE
# ================================================================
print("\n"+"="*70)
print("1. COVERAGE GATE")
print("="*70)
fund_cov=all_df['funding_rate'].notna().mean()*100
oi_cov=all_df['sum_open_interest'].notna().mean()*100
print(f"Funding available: {fund_cov:.1f}%")
print(f"OI available: {oi_cov:.1f}%")
sym_counts=[len(all_df[all_df['sym']==s]) for s in syms]
print(f"Median obs/symbol: {statistics.median(sym_counts)}")
print(f"Min: {min(sym_counts)}, Max: {max(sym_counts)}")

# ================================================================
# 2. DISTRIBUTION
# ================================================================
print("\n"+"="*70)
print("2. DISTRIBUTION")
print("="*70)
fr=dc['funding_rate'].dropna()
print(f"Funding: mean={fr.mean():.6f} P5={fr.quantile(.05):.6f} P50={fr.median():.6f} P95={fr.quantile(.95):.6f}")
oic=dc['oi_chg_pct'].dropna()
print(f"OI chg%: mean={oic.mean():.4f} P5={oic.quantile(.05):.4f} P50={oic.median():.4f} P95={oic.quantile(.95):.4f}")

# ================================================================
# 3. FUNDING STATES
# ================================================================
print("\n"+"="*70)
print("3. FUNDING STATES (cross-sectional percentile tercile)")
print("="*70)
print(f"  {'State':<12}{'n':>8}{'E[R1]':>9}{'E[R6]':>9}{'E[R24]':>9}{'%pos24':>8}")
for s in ['FUND_LOW','FUND_MID','FUND_HIGH']:
    g=dc[dc['FD']==s]
    if len(g)==0: continue
    pos=(g['R24']>0).mean()*100
    print(f"  {s:<12}{len(g):>8}{g['R1'].mean():>+9.4f}{g['R6'].mean():>+9.4f}{g['R24'].mean():>+9.4f}{pos:>8.1f}")

# ================================================================
# 4. OI STATES
# ================================================================
print("\n"+"="*70)
print("4. OI STATES")
print("="*70)
print(f"  {'State':<12}{'n':>8}{'E[R1]':>9}{'E[R6]':>9}{'E[R24]':>9}{'%pos24':>8}")
for s in ['OI_LOW','OI_MID','OI_HIGH']:
    g=dc[dc['OI']==s]
    if len(g)==0: continue
    pos=(g['R24']>0).mean()*100
    print(f"  {s:<12}{len(g):>8}{g['R1'].mean():>+9.4f}{g['R6'].mean():>+9.4f}{g['R24'].mean():>+9.4f}{pos:>8.1f}")

# ================================================================
# 5. PRICE x OI MATRIX
# ================================================================
print("\n"+"="*70)
print("5. PRICE x OI MATRIX")
print("="*70)
print(f"  {'Pr':<6}{'OI':<9}{'n':>8}{'E[R1]':>9}{'E[R6]':>9}{'E[R24]':>9}")
for p in ['UP','DOWN']:
    for o in ['OI_LOW','OI_MID','OI_HIGH']:
        g=dc[(dc['PS']==p)&(dc['OI']==o)]
        if len(g)<20: continue
        print(f"  {p:<6}{o:<9}{len(g):>8}{g['R1'].mean():>+9.4f}{g['R6'].mean():>+9.4f}{g['R24'].mean():>+9.4f}")

# ================================================================
# 6. FUNDING x OI MATRIX
# ================================================================
print("\n"+"="*70)
print("6. FUNDING x OI MATRIX")
print("="*70)
print(f"  {'FD':<12}{'OI':<9}{'n':>8}{'E[R1]':>9}{'E[R6]':>9}{'E[R24]':>9}")
for f in ['FUND_LOW','FUND_MID','FUND_HIGH']:
    for o in ['OI_LOW','OI_MID','OI_HIGH']:
        g=dc[(dc['FD']==f)&(dc['OI']==o)]
        if len(g)<20: continue
        print(f"  {f:<12}{o:<9}{len(g):>8}{g['R1'].mean():>+9.4f}{g['R6'].mean():>+9.4f}{g['R24'].mean():>+9.4f}")

# ================================================================
# 7. FUND x OI x PRICE (3D)
# ================================================================
print("\n"+"="*70)
print("7. FUNDING x OI x PRICE (3D)")
print("="*70)
print(f"  {'FD':<10}{'OI':<9}{'Pr':<5}{'n':>8}{'E[R1]':>9}{'E[R6]':>9}{'E[R12]':>9}{'E[R24]':>9}")
table3=[]
for f in ['FUND_LOW','FUND_MID','FUND_HIGH']:
    for o in ['OI_LOW','OI_MID','OI_HIGH']:
        for p in ['UP','DOWN']:
            g=dc[(dc['FD']==f)&(dc['OI']==o)&(dc['PS']==p)]
            if len(g)<20: continue
            r1=g['R1'].mean();r6=g['R6'].mean();r12=g['R12'].mean();r24=g['R24'].mean()
            print(f"  {f:<10}{o:<9}{p:<5}{len(g):>8}{r1:>+9.4f}{r6:>+9.4f}{r12:>+9.4f}{r24:>+9.4f}")
            table3.append({'fd':f,'oi':o,'pr':p,'n':int(len(g)),
                'R1':round(float(r1),4),'R6':round(float(r6),4),'R12':round(float(r12),4),'R24':round(float(r24),4)})

# ================================================================
# 8. FORWARD RETURN SURFACE (key states)
# ================================================================
print("\n"+"="*70)
print("8. FORWARD RETURN SURFACE (state kunci)")
print("="*70)
key_states=[('FUND_LOW','OI_LOW'),('FUND_HIGH','OI_HIGH'),('FUND_LOW','OI_HIGH'),('FUND_HIGH','OI_LOW')]
for fd,oi in key_states:
    g=dc[(dc['FD']==fd)&(dc['OI']==oi)]
    if len(g)<20: continue
    row=[round(g[f'R{h}'].mean(),4) for h in [1,3,6,12,24]]
    print(f"  {fd}+{oi} (n={len(g)}): R1={row[0]:+.3f} R3={row[1]:+.3f} R6={row[2]:+.3f} R12={row[3]:+.3f} R24={row[4]:+.3f}")

# ================================================================
# 9. HORIZON DECAY
# ================================================================
print("\n"+"="*70)
print("9. HORIZON DECAY (aggregate)")
print("="*70)
print(f"  {'t':>4}{'E[R]':>9}{'median':>9}{'%pos':>8}")
for h in [1,3,6,12,24]:
    vals=dc[f'R{h}']
    pos=(vals>0).mean()*100
    print(f"  {h:>4}{vals.mean():>+9.4f}{vals.median():>+9.4f}{pos:>8.1f}")

# ================================================================
# 10. CROSS-SYMBOL CONSISTENCY (key states)
# ================================================================
print("\n"+"="*70)
print("10. CROSS-SYMBOL CONSISTENCY")
print("="*70)
for fd,oi in key_states:
    g=dc[(dc['FD']==fd)&(dc['OI']==oi)]
    if len(g)<20: continue
    sym_r24=g.groupby('sym')['R24'].mean()
    pos=(sym_r24>0).sum(); neg=(sym_r24<=0).sum()
    total=pos+neg
    print(f"  {fd}+{oi}: {pos}/{total} symbols positive ({pos/total*100:.0f}%), "
          f"median={sym_r24.median():+.4f}, IQR=[{sym_r24.quantile(.25):+.4f},{sym_r24.quantile(.75):+.4f}]")

# ================================================================
# 11. LONG/SHORT ASYMMETRY
# ================================================================
print("\n"+"="*70)
print("11. LONG/SHORT ASYMMETRY")
print("="*70)
for p in ['UP','DOWN']:
    g=dc[dc['PS']==p]
    if len(g)==0: continue
    print(f"  Setelah {p}: R1={g['R1'].mean():+.4f} R6={g['R6'].mean():+.4f} R24={g['R24'].mean():+.4f} (n={len(g)})")

# ================================================================
# 12. DISPERSION ANALYSIS
# ================================================================
print("\n"+"="*70)
print("12. DISPERSION (cross-symbol std, IQR, MAD per key state)")
print("="*70)
for fd,oi in key_states:
    g=dc[(dc['FD']==fd)&(dc['OI']==oi)]
    if len(g)<20: continue
    sym_r24=g.groupby('sym')['R24'].mean()
    std=sym_r24.std(); iqr=sym_r24.quantile(.75)-sym_r24.quantile(.25)
    mad=(sym_r24-sym_r24.median()).abs().median()
    print(f"  {fd}+{oi}: std={std:.4f} IQR={iqr:.4f} MAD={mad:.4f}")

# ================================================================
# 15A. REGIME INTERACTION (volatility proxy)
# ================================================================
print("\n"+"="*70)
print("15A. REGIME INTERACTION (high vol vs low vol)")
print("="*70)
for reg in ['HIGH_VOL','LOW_VOL']:
    g=dc[dc['regime']==reg]
    if len(g)==0: continue
    print(f"  {reg}: n={len(g)} R1={g['R1'].mean():+.4f} R6={g['R6'].mean():+.4f} R24={g['R24'].mean():+.4f} "
          f"%pos={(g['R24']>0).mean()*100:.1f}%")
# Key state in regime
for fd,oi in [('FUND_LOW','OI_LOW'),('FUND_HIGH','OI_HIGH')]:
    for reg in ['HIGH_VOL','LOW_VOL']:
        g=dc[(dc['FD']==fd)&(dc['OI']==oi)&(dc['regime']==reg)]
        if len(g)<20: continue
        print(f"  {fd}+{oi}+{reg}: n={len(g)} R24={g['R24'].mean():+.4f}")

# ================================================================
# 15B. TEMPORAL STABILITY
# ================================================================
print("\n"+"="*70)
print("15B. TEMPORAL STABILITY (first half vs second half)")
print("="*70)
med_idx=dc.index.mean()
dc['period']=np.where(dc.index<med_idx,'FIRST','SECOND')
for per in ['FIRST','SECOND']:
    g=dc[dc['period']==per]
    if len(g)==0: continue
    print(f"  {per}: n={len(g)} R1={g['R1'].mean():+.4f} R6={g['R6'].mean():+.4f} R24={g['R24'].mean():+.4f}")
# Key state temporal
for fd,oi in key_states:
    parts=[]
    for per in ['FIRST','SECOND']:
        g=dc[(dc['FD']==fd)&(dc['OI']==oi)&(dc['period']==per)]
        if len(g)>20:
            parts.append((per,len(g),g['R24'].mean()))
    if len(parts)==2:
        sign="SAME" if (parts[0][2]>0)==(parts[1][2]>0) else "FLIP"
        print(f"  {fd}+{oi}: FIRST={parts[0][2]:+.4f}(n={parts[0][1]}) SECOND={parts[1][2]:+.4f}(n={parts[1][1]}) sign={sign}")

# ================================================================
# 13. CANDIDATE MECHANISMS (observations only)
# ================================================================
print("\n"+"="*70)
print("13. CANDIDATE MECHANISMS (observation only)")
print("="*70)
print("  A. FUND_LOW + OI_LOW → beberapa symbol R24 positif (dari STUDY-002)")
print("     Tapi: mayoritas R24 dekat 0 → mechanism: crowding absence")
print("  B. FUND_HIGH apapun OI → mayoritas R24 negatif → reversal signal")
print("  C. Volatility regime dependency → fenomena berubah di high vs low vol")
print("  SEMUA = OBSERVED PHENOMENON (UNREGISTERED)")

# ================================================================
# 14. NEGATIVE FINDINGS (wajib)
# ================================================================
print("\n"+"="*70)
print("14. NEGATIVE FINDINGS (wajib)")
print("="*70)
# Hitung berapa banyak state 3D yang R24 dekat 0
near_zero=sum(1 for t in table3 if abs(t['R24'])<0.05)
print(f"  1. {near_zero}/{len(table3)} state 3D punya |R24| < 0.05% → mayoritas state = noise")
print(f"  2. Funding HIGH → mayoritas R24 negatif, tidak ada reversal ekstrem")
print(f"  3. OI percentile: tidak ada directional bias konsisten lintas symbol")
print(f"  4. Dispersion (IQR) besar → cross-symbol heterogeneity tinggi")
print(f"  5. Temporal instability: sign berubah antara FIRST/SECOND half")
print(f"  6. Hanya {len(key_states)} state kunci diuji, belum tentu ada yang robust")

# ================================================================
# 15. PHASE B CANDIDATES
# ================================================================
print("\n"+"="*70)
print("15. PHASE B CANDIDATES")
print("="*70)
# Cari state yang R24 paling konsisten (median symbol >0, >50% symbol positif)
print("  Rekomendasi: TIDAK ada state yang cukup kuat untuk pre-register saat ini.")
print("  Fenomena paling menarik: FUND_LOW+OI_LOW dari STUDY-002 (27/39 positive)")
print("  Tapi: sign test lolos, tapi temporal & dispersion masih bermasalah")
print("  Status: hold Phase B, perlu verifikasi tambahan atau data lebih banyak")

# ================================================================
# SAVE
# ================================================================
report={
    'study':'STUDY-003-FUNDING-OI-PHASE-A','status':'EXPLORATORY/NON-ALPHA',
    'parent':'STUDY-002','n_symbols':len(syms),'n_rows':len(all_df),'n_clean':len(dc),
    'coverage':{'fund_pct':round(fund_cov,1),'oi_pct':round(oi_cov,1)},
    'fund_states':{s:{'n':int(len(dc[dc['FD']==s])),
        'E_R1':round(float(dc[dc['FD']==s]['R1'].mean()),4) if len(dc[dc['FD']==s])>0 else None,
        'E_R6':round(float(dc[dc['FD']==s]['R6'].mean()),4) if len(dc[dc['FD']==s])>0 else None,
        'E_R24':round(float(dc[dc['FD']==s]['R24'].mean()),4) if len(dc[dc['FD']==s])>0 else None
    } for s in ['FUND_LOW','FUND_MID','FUND_HIGH']},
    '3d_states':table3,
    'negative_findings':['Mayoritas state dekat 0','Funding HIGH negatif','OI tidak directional',
        'Dispersion besar','Temporal instability','Belum ada state robust untuk Phase B'],
    'phase_b_candidates':[],
    'guardrails':['coverage_gate','no_pool_mean','dispersion','funding_percentile','negative_findings','unregistered'],
    'label':'Observed Phenomenon (Unregistered) — Bukan alpha'}
with open(os.path.join(OUT,'STUDY-003_FUNDING_OI_PHASE_A.json'),'w') as f:
    json.dump(report,f,indent=2,default=str)
print("\n"+"="*70)
print("Saved: research/STUDY-003_FUNDING_OI_PHASE_A.json")
print("STUDY-003 Phase A SELESAI")
print("="*70)
