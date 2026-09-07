#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-002-FUNDING-OI-PHASE-A - Phenomenon Discovery (EXPLORATORY / NON-ALPHA)
=============================================================================
Parent: STUDY-002 (baru, terpisah dari STUDY-001)
Status: EXPLORATORY / NON-ALPHA
Tujuan: menemukan fenomena, BUKAN mencari strategi.

GUARDRAIL PHASE A:
1. JANGAN pilih threshold terbaik (bukan "percentile 93 terbaik")
2. JANGAN TP/SL optimization
3. JANGAN Train/Val/Test untuk memilih state terbaik
4. JANGAN MTC terhadap semua descriptive states (catat jumlah eksplorasi saja)
5. Label fenomena = "Observed phenomenon - unregistered", bukan "edge"

PISAHKAN:
- Cross-sectional normalization: funding percentile per symbol, OI percentile per symbol
- Time-series normalization: funding z-score terhadap history symbol, OI z-score

OUTPUT: 15 bagian (data coverage, missingness, distribution, funding states,
OI states, Price×OI matrix, Funding×OI matrix, Funding×OI×Price state,
forward-return surface, horizon decay, cross-symbol consistency, long/short
asymmetry, candidate mechanisms, negative findings, candidates for Phase B)
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
    else:
        df['sum_open_interest']=np.nan
    if os.path.exists(f):
        fund=pd.read_parquet(f); fund.index=pd.to_datetime(fund.index,utc=True)
        df=df.join(fund[['funding_rate']],how='left')
    else:
        df['funding_rate']=np.nan
    return df

print("="*70)
print("STUDY-002-FUNDING-OI-PHASE-A - Phenomenon Discovery (NON-ALPHA)")
print("="*70)

# ============ BUILD DATASET with features ============
symbols=sorted(os.listdir(DATA_DIR))
print(f"\nMembangun dataset: {len(symbols)} simbol")
rows_by_symbol={}  # symbol -> list of row dicts
all_rows=[]
missing={}

for si,symbol in enumerate(symbols):
    df=load_symbol(symbol)
    if df is None: continue
    n=len(df)
    closes=df['close'].values; volumes=df['volume'].values
    oi=df['sum_open_interest'].values; fund=df['funding_rate'].values
    
    # === Time-series features (ts-normalization) ===
    # volume z-score (rolling 100)
    vol_series=pd.Series(volumes)
    vol_mean=vol_series.rolling(100).mean(); vol_std=vol_series.rolling(100).std()
    vol_z=np.where(vol_std>0,(volumes-vol_mean)/vol_std,np.nan)
    
    # funding z-score (rolling 100) - time-series normalization
    fund_series=pd.Series(fund)
    fund_mean=fund_series.rolling(100).mean(); fund_std=fund_series.rolling(100).std()
    fund_z=np.where(fund_std>0,(fund-fund_mean)/fund_std,np.nan)
    
    # OI z-score (rolling 100) - time-series
    oi_series=pd.Series(oi)
    oi_mean=oi_series.rolling(100).mean(); oi_std=oi_series.rolling(100).std()
    oi_z=np.where(oi_std>0,(oi-oi_mean)/oi_std,np.nan)
    
    # ΔOI % (lag 1)
    oi_change=np.full(n,np.nan)
    oi_change[1:]=np.where(pd.Series(oi).shift(1).values[1:]>0,
                           (oi[1:]-pd.Series(oi).shift(1).values[1:])/pd.Series(oi).shift(1).values[1:]*100,
                           np.nan)
    
    rows=[]
    for i in range(20,n-24):  # need 24 forward bars
        r={}
        r['symbol']=symbol
        r['idx']=i
        r['ts']=str(df.index[i])
        r['close']=float(closes[i])
        # forward returns (long convention sign)
        for h in [1,3,6,12,24]:
            r[f'R{h}']=(closes[i+h]/closes[i]-1)*100
        # features
        r['oi_raw']=float(oi[i]) if not np.isnan(oi[i]) else None
        r['oi_change_pct']=float(oi_change[i]) if not np.isnan(oi_change[i]) else None
        r['oi_ts_zscore']=float(oi_z[i]) if not np.isnan(oi_z[i]) else None
        r['funding_raw']=float(fund[i]) if not np.isnan(fund[i]) else None
        r['funding_ts_zscore']=float(fund_z[i]) if not np.isnan(fund_z[i]) else None
        r['vol_ts_zscore']=float(vol_z[i]) if not np.isnan(vol_z[i]) else None
        r['price_return_1']=(closes[i]/closes[i-1]-1)*100  # prior 1bar price move direction
        rows.append(r)
    rows_by_symbol[symbol]=rows
    all_rows.extend(rows)
    missing[symbol]={'n':n,'rows_kept':len(rows)}

print(f"TOTAL rows: {len(all_rows)}")

# === Cross-sectional normalization (percentile per symbol) ===
# Fungsi: rank → percentile dalam symbol (0-1)
for sym,rows in rows_by_symbol.items():
    # funding percentile
    fvals=[r['funding_raw'] for r in rows if r['funding_raw'] is not None]
    if fvals:
        fsorted=sorted(fvals)
        def f_rank(x):
            if x is None: return None
            lo=sum(1 for v in fsorted if v<=x)
            return lo/len(fsorted)
        for r in rows:
            r['funding_cs_percentile']=f_rank(r['funding_raw'])
            # OI percentile
    oivals=[r['oi_raw'] for r in rows if r['oi_raw'] is not None]
    if oivals:
        osorted=sorted(oivals)
        for r in rows:
            if r['oi_raw'] is None: r['oi_cs_percentile']=None
            else:
                lo=sum(1 for v in osorted if v<=r['oi_raw'])
                r['oi_cs_percentile']=lo/len(osorted)

# Save features dataset
with open(os.path.join(RESEARCH_DIR,'study002_features.json'),'w') as f:
    json.dump(all_rows,f)

print("Features saved (cross-sectional + time-series normalization)")

# ================================================================
# STATE DEFINITION (descriptive, BUKAN trading threshold)
# ================================================================
# Price state: prior 1bar price return sign
# OI state: ΔOI sign (or OI percentile)
# Funding state: tercile (low/neutral/high)

# ================================================================
# 2. DISTRIBUTION REPORT
# ================================================================
print("\n"+"="*70)
print("2-3. DISTRIBUTION & DATA COVERAGE / MISSINGNESS")
print("="*70)
# funding raw distribution (cross-symbol pooled + per-symbol spread)
fr=[r['funding_raw'] for r in all_rows if r['funding_raw'] is not None]
fr_sorted=sorted(fr)
def q(arr,p):
    return arr[int(len(arr)*p)]
print(f"Funding raw: mean={statistics.mean(fr):.6f}, P5={q(fr_sorted,.05):.6f}, "
      f"P50={q(fr_sorted,.5):.6f}, P95={q(fr_sorted,.95):.6f}")
oic=[r['oi_change_pct'] for r in all_rows if r['oi_change_pct'] is not None]
oic_sorted=sorted(oic)
print(f"OI change %: mean={statistics.mean(oic):.3f}, P5={q(oic_sorted,.05):.3f}, "
      f"P50={q(oic_sorted,.5):.3f}, P95={q(oic_sorted,.95):.3f}")
# Missingness
has_oi=sum(1 for r in all_rows if r['oi_raw'] is not None)
has_fund=sum(1 for r in all_rows if r['funding_raw'] is not None)
print(f"Missingness: OI available {has_oi}/{len(all_rows)} ({has_oi/len(all_rows)*100:.1f}%), "
      f"Funding available {has_fund}/{len(all_rows)} ({has_fund/len(all_rows)*100:.1f}%)")

# ================================================================
# STATE SPACE MATRICES
# ================================================================
def state_of(r):
    """Describe positional state (descriptive)."""
    # Price state
    price_r=r.get('price_return_1')
    p_state='UP' if (price_r is not None and price_r>0) else ('DOWN' if (price_r is not None and price_r<0) else 'FLAT')
    # OI state by percentile (cross-sectional) tercile
    oip=r.get('oi_cs_percentile')
    if oip is None: oi_state='NA'
    elif oip<0.33: oi_state='OI_LOW'
    elif oip>0.66: oi_state='OI_HIGH'
    else: oi_state='OI_MID'
    # Funding state by percentile (cross-sectional) tercile
    fp=r.get('funding_cs_percentile')
    if fp is None: fund_state='NA'
    elif fp<0.33: fund_state='FUND_LOW'
    elif fp>0.66: fund_state='FUND_HIGH'
    else: fund_state='FUND_MID'
    return p_state,oi_state,fund_state

# Forward-return surface helper
def summarize(rows, horizons=[1,3,6,12,24]):
    out={}
    for h in horizons:
        vals=[r[f'R{h}'] for r in rows if r.get(f'R{h}') is not None]
        if vals: out[f'R{h}']={'mean':round(statistics.mean(vals),4),
                               'median':round(statistics.median(vals),4),
                               'n':len(vals)}
    return out

# Build state-tagged rows
tagged=[]
for r in all_rows:
    if r.get('funding_cs_percentile') is None or r.get('oi_cs_percentile') is None:
        continue
    ps,oi_s,fd_s=state_of(r)
    if 'NA' in (ps,oi_s,fd_s): continue
    r['_ps']=ps;r['_oi']=oi_s;r['_fd']=fd_s
    tagged.append(r)
print(f"\nTagged rows (lengkap semua state): {len(tagged)}")

# ================================================================
# 6. PRICE × OI MATRIX
# ================================================================
print("\n"+"="*70)
print("6. PRICE × OI MATRIX (E[R1], E[R6], E[R24])")
print("="*70)
print(f"  {'Price':<6}{'OI':<9}{'n':>6}{'E[R1]':>9}{'E[R6]':>9}{'E[R24]':>9}")
print("  "+"-"*50)
for ps in ['UP','DOWN']:
    for oi_s in ['OI_LOW','OI_MID','OI_HIGH']:
        sub=[r for r in tagged if r['_ps']==ps and r['_oi']==oi_s]
        if len(sub)<20: continue
        e1=statistics.mean([r['R1'] for r in sub]);e6=statistics.mean([r['R6'] for r in sub]);e24=statistics.mean([r['R24'] for r in sub])
        print(f"  {ps:<6}{oi_s:<9}{len(sub):>6}{e1:>+9.3f}{e6:>+9.3f}{e24:>+9.3f}")

# ================================================================
# 7. FUNDING × OI MATRIX
# ================================================================
print("\n"+"="*70)
print("7. FUNDING × OI MATRIX (E[R1], E[R6], E[R24])")
print("="*70)
print(f"  {'Funding':<10}{'OI':<9}{'n':>6}{'E[R1]':>9}{'E[R6]':>9}{'E[R24]':>9}")
print("  "+"-"*52)
for fd_s in ['FUND_LOW','FUND_MID','FUND_HIGH']:
    for oi_s in ['OI_LOW','OI_MID','OI_HIGH']:
        sub=[r for r in tagged if r['_fd']==fd_s and r['_oi']==oi_s]
        if len(sub)<20: continue
        e1=statistics.mean([r['R1'] for r in sub]);e6=statistics.mean([r['R6'] for r in sub]);e24=statistics.mean([r['R24'] for r in sub])
        print(f"  {fd_s:<10}{oi_s:<9}{len(sub):>6}{e1:>+9.3f}{e6:>+9.3f}{e24:>+9.3f}")

# ================================================================
# 8. FUNDING × OI × PRICE STATE (8 combos - x-y-z)
# ================================================================
print("\n"+"="*70)
print("8. FUNDING × OI × PRICE STATE (E[R1], E[R6], E[R24])")
print("="*70)
print(f"  {'Funding':<9}{'OI':<8}{'Pr':<5}{'n':>6}{'E[R1]':>9}{'E[R6]':>9}{'E[R24]':>9}")
print("  "+"-"*58)
table=[]
for fd_s in ['FUND_LOW','FUND_MID','FUND_HIGH']:
    for oi_s in ['OI_LOW','OI_MID','OI_HIGH']:
        for ps in ['UP','DOWN']:
            sub=[r for r in tagged if r['_fd']==fd_s and r['_oi']==oi_s and r['_ps']==ps]
            if len(sub)<20: continue
            e1=statistics.mean([r['R1'] for r in sub]);e6=statistics.mean([r['R6'] for r in sub]);e24=statistics.mean([r['R24'] for r in sub])
            print(f"  {fd_s:<9}{oi_s:<8}{ps:<5}{len(sub):>6}{e1:>+9.3f}{e6:>+9.3f}{e24:>+9.3f}")
            table.append({'funding':fd_s,'oi':oi_s,'price':ps,'n':len(sub),
                          'E_R1':round(e1,4),'E_R6':round(e6,4),'E_R24':round(e24,4)})

# ================================================================
# 9. FORWARD RETURN SURFACE + 10. HORIZON DECAY
# ================================================================
# Menampilkan full horizon decay untuk state extreme yang menonjol
print("\n"+"="*70)
print("9-10. FORWARD RETURN SURFACE + HORIZON DECAY (state ekstrem)")
print("="*70)
extreme_states=[
    ('FUND_HIGH','OI_HIGH','UP'),
    ('FUND_HIGH','OI_HIGH','DOWN'),
    ('FUND_HIGH','OI_LOW','UP'),
    ('FUND_LOW','OI_LOW','DOWN'),
    ('FUND_LOW','OI_HIGH','UP'),
    ('FUND_LOW','OI_LOW','UP'),
]
for (fd_s,oi_s,ps) in extreme_states:
    sub=[r for r in tagged if r['_fd']==fd_s and r['_oi']==oi_s and r['_ps']==ps]
    if len(sub)<20: continue
    decay=[]
    for h in [1,3,6,12,24]:
        vals=[r[f'R{h}'] for r in sub]
        decay.append(round(statistics.mean(vals),4))
    print(f"  {fd_s}+{oi_s}+{ps} (n={len(sub)}): R1={decay[0]:+.3f} R3={decay[1]:+.3f} "
          f"R6={decay[2]:+.3f} R12={decay[3]:+.3f} R24={decay[4]:+.3f}")

# ================================================================
# 11. CROSS-SYMBOL CONSISTENCY (untuk state kunci)
# ================================================================
print("\n"+"="*70)
print("11. CROSS-SYMBOL CONSISTENCY (FUND_HIGH+OI_HIGH+UP pada R6 per symbol)")
print("="*70)
key_state=('FUND_HIGH','OI_HIGH','UP')
sym_res=[]
for sym in symbols:
    sub=[r for r in tagged if r['symbol']==sym and (r['_fd'],r['_oi'],r['_ps'])==key_state]
    if len(sub)>=10:
        e6=statistics.mean([r['R6'] for r in sub])
        sym_res.append((sym,len(sub),e6))
        print(f"  {sym}: n={len(sub)}, E[R6]={e6:+.3f}%")
n_pos=sum(1 for _,_,e in sym_res if e>0)
print(f"  {n_pos}/{len(sym_res)} symbol positif pada state ini")

# ================================================================
# 12. LONG/SHORT ASYMMETRY (price direction)
# ================================================================
print("\n"+"="*70)
print("12. LONG/SHORT ASYMMETRY (state FLAT/UP vs DOWN berikutnya)")
print("="*70)
up_after=[r for r in tagged if r['_ps']=='UP']; down_after=[r for r in tagged if r['_ps']=='DOWN']
if len(up_after)>20 and len(down_after)>20:
    print(f"  Setelah Price UP : E[R1]={statistics.mean([r['R1'] for r in up_after]):+.4f}%, "
          f"E[R6]={statistics.mean([r['R6'] for r in up_after]):+.4f}%, E[R24]={statistics.mean([r['R24'] for r in up_after]):+.4f}%")
    print(f"  Setelah Price DOWN: E[R1]={statistics.mean([r['R1'] for r in down_after]):+.4f}%, "
          f"E[R6]={statistics.mean([r['R6'] for r in down_after]):+.4f}%, E[R24]={statistics.mean([r['R24'] for r in down_after]):+.4f}%")

# ================================================================
# SAVE REPORT
# ================================================================
report={
    'study':'STUDY-002-FUNDING-OI-PHASE-A',
    'status':'EXPLORATORY/NON-ALPHA',
    'parent':'STUDY-002',
    'goal':'Phenomenon discovery - BUKAN strategy search',
    'guardrails':['no threshold selection','no TP/SL opt','no train/val/test state selection',
                  'no MTC on descriptive states','label=observed phenomenon unregistered'],
    'n_symbols':len(symbols),
    'n_rows':len(all_rows),
    'n_tagged':len(tagged),
    'distributions':{
        'funding_raw':{'mean':round(statistics.mean(fr),7),'P5':round(q(fr_sorted,.05),7),
                       'P50':round(q(fr_sorted,.5),7),'P95':round(q(fr_sorted,.95),7)},
        'oi_change_pct':{'mean':round(statistics.mean(oic),4),'P5':round(q(oic_sorted,.05),4),
                         'P50':round(q(oic_sorted,.5),4),'P95':round(q(oic_sorted,.95),4)},
        'missing':{'oi_avail_pct':round(has_oi/len(all_rows)*100,1),
                   'funding_avail_pct':round(has_fund/len(all_rows)*100,1)}
    },
    'states_3d':table,
    'n_explorations':len(table),
    'note':'Fenomena yang menonjol = OBSERVED - unregistered. Belum pre-registered.',
    'candidate_for_phase_b':[],  # diisi manual setelah review
    'negative_findings':[],
}
with open(os.path.join(RESEARCH_DIR,'STUDY-002_FUNDING_OI_PHASE_A.json'),'w') as f:
    json.dump(report,f,indent=2,default=str)
print("\n"+"="*70)
print("Laporan disimpan ke research/STUDY-002_FUNDING_OI_PHASE_A.json")
print("="*70)
