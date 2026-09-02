#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-005 — OOS Temporal Split (Ketat, Per-Symbol, Frozen State)
=================================================================
State: FUND_LOW + OI_LOW + HIGH_VOL → positive 24h drift
TIDAK BOLEH: threshold baru, filter tambahan, optimasi, ubah horizon

Split (per symbol, berbasis timestamp):
  TRAIN  : Jul 2024 – Jun 2025
  VAL    : Jul 2025 – Des 2025
  TEST   : Jan 2026 – Agu 2026

Evaluasi:
  Primary   : E[R24]
  Secondary : % symbol positive
  Tertiary  : effect size decay per horizon
"""
import json, os, random, statistics, math
import pandas as pd, numpy as np
random.seed(42); np.random.seed(42)

DATA='/home/rtk/Bot-Multi-Edge-metrics/data'
KDIR=DATA+'/klines'; MDIR=DATA+'/metrics'; FDIR=DATA+'/funding'
OUT='/home/rtk/enterprise-trading-platform/layer5_alpha_engine/research'
os.makedirs(OUT, exist_ok=True)

# Temporal split boundaries (tz-aware UTC)
TRAIN_END=pd.Timestamp('2025-06-30', tz='UTC')
VAL_END=pd.Timestamp('2025-12-31', tz='UTC')

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
print("STUDY-005 — OOS TEMPORAL SPLIT (Per-Symbol, Frozen State)")
print("State: FUND_LOW + OI_LOW + HIGH_VOL → E[R24]>0")
print("Tidak ada optimasi. Tidak ada filter baru.")
print("="*70)

syms=sorted(os.listdir(KDIR))
frames=[]
for sym in syms:
    df=load(sym)
    if df is None: continue
    c=df['close']
    for h in [1,3,6,12,24]: df[f'R{h}']=(c.shift(-h)/c-1)*100
    df['sym']=sym
    df['rv']=df['close'].pct_change().rolling(100).std()
    frames.append(df)

all_df=pd.concat(frames)
print(f"Total rows: {len(all_df)}, Symbols: {len(syms)}")

# Cross-sectional percentile per symbol
all_df['fund_pct']=all_df.groupby('sym')['funding_rate'].rank(pct=True)
all_df['oi_pct']=all_df.groupby('sym')['sum_open_interest'].rank(pct=True)
# State flags (FROZEN)
all_df['FUND_LOW']=all_df['fund_pct']<0.33
all_df['OI_LOW']=all_df['oi_pct']<0.33
vol_med=all_df['rv'].median()
all_df['HIGH_VOL']=all_df['rv']>vol_med
all_df['STATE']=all_df['FUND_LOW']&all_df['OI_LOW']&all_df['HIGH_VOL']

# Drop rows missing R24
dc=all_df.dropna(subset=['R1','R3','R6','R12','R24','fund_pct','oi_pct','rv']).copy()
print(f"Clean rows: {len(dc)}")

# ================================================================
# TEMPORAL SPLIT (per symbol, timestamp-based)
# ================================================================
dc['split']=np.where(dc.index<=TRAIN_END,'TRAIN',
            np.where(dc.index<=VAL_END,'VAL','TEST'))
print(f"\nSplit distribution:")
for s in ['TRAIN','VAL','TEST']:
    sub=dc[dc['split']==s]
    st=sub[sub['STATE']]
    print(f"  {s}: all={len(sub)} state={len(st)} state%={len(st)/len(sub)*100:.1f}%")

# ================================================================
# PER-SPLIT ANALYSIS
# ================================================================
def analyze_window(df, split_name):
    """Analisis state frozen pada satu window"""
    state=df[df['STATE']]
    all_rows=df
    results={}
    results['n_total']=len(all_rows)
    results['n_state']=len(state)
    
    if len(state)==0:
        print(f"  {split_name}: TIDAK ADA EVENT STATE!")
        return results
    
    for h in [1,3,6,12,24]:
        vals=state[f'R{h}']
        all_vals=all_rows[f'R{h}']
        pos_sym=(state.groupby('sym')[f'R{h}'].mean()>0).sum()
        tot_sym=len(state.groupby('sym')[f'R{h}'].mean())
        results[f'R{h}']={
            'mean':round(float(vals.mean()),4),
            'median':round(float(vals.median()),4),
            'std':round(float(vals.std()),4),
            '%pos_sym':round(pos_sym/tot_sym*100,1) if tot_sym>0 else 0,
            'pos_sym':pos_sym,
            'n_sym':tot_sym,
            'baseline_mean':round(float(all_vals.mean()),4)}
    
    # Net after cost (R24, 8bps)
    gross_bps=state['R24'].mean()*100
    results['net8bps']=round(gross_bps-16,1)
    results['net10bps']=round(gross_bps-20,1)
    results['net12bps']=round(gross_bps-24,1)
    
    return results

print("\n"+"="*70)
print("PRIMARY: E[R24] per window")
print("="*70)
train_r=analyze_window(dc[dc['split']=='TRAIN'],'TRAIN')
val_r=analyze_window(dc[dc['split']=='VAL'],'VAL')
test_r=analyze_window(dc[dc['split']=='TEST'],'TEST')

for name,r in [('TRAIN',train_r),('VAL',val_r),('TEST',test_r)]:
    if 'R24' not in r:
        continue
    print(f"  {name}: n={r['n_state']}, E[R24]={r['R24']['mean']:+.4f}%, "
          f"median={r['R24']['median']:+.4f}%, "
          f"%sym={r['R24']['pos_sym']}/{r['R24']['n_sym']} ({r['R24']['%pos_sym']}%)")
    print(f"    Net(8bps)={r['net8bps']:+.1f}bps, Net(10bps)={r['net10bps']:+.1f}bps, "
          f"Net(12bps)={r['net12bps']:+.1f}bps")

# ================================================================
# SECONDARY: Effect size decay per window
# ================================================================
print("\n"+"="*70)
print("SECONDARY: Effect size decay (per horizon)")
print("="*70)
print(f"  {'horizon':<10}{'TRAIN':>10}{'VAL':>10}{'TEST':>10}{'TEST baseline':>14}{'lift':>8}")
for h in [1,3,6,12,24]:
    t=train_r.get(f'R{h}',{}).get('mean',0)
    v=val_r.get(f'R{h}',{}).get('mean',0)
    ts=test_r.get(f'R{h}',{}).get('mean',0)
    bl=test_r.get(f'R{h}',{}).get('baseline_mean',0)
    lift=ts-bl if ts is not None and bl is not None else 0
    print(f"  R{h:<8}{t:>+10.4f}{v:>+10.4f}{ts:>+10.4f}{bl:>+14.4f}{lift:>+8.4f}")

# ================================================================
# TERTIARY: Per-symbol in TEST window
# ================================================================
print("\n"+"="*70)
print("TERTIARY: Per-symbol R24 in TEST window")
print("="*70)
test_state=dc[(dc['split']=='TEST')&dc['STATE']]
sym_r24=test_state.groupby('sym')['R24'].mean().sort_values(ascending=False)
pos_n=(sym_r24>0).sum()
neg_n=(sym_r24<=0).sum()
print(f"  Positif: {pos_n}, Negatif: {neg_n}, Total: {len(sym_r24)}")
print(f"  Median R24: {sym_r24.median():+.4f}%")
print(f"  Mean R24: {sym_r24.mean():+.4f}%")
print(f"  IQR: [{sym_r24.quantile(.25):+.4f}, {sym_r24.quantile(.75):+.4f}]")
print(f"  Top 5:")
for sym,val in sym_r24.head(5).items():
    print(f"    {sym}: {val:+.4f}%")
print(f"  Bottom 5:")
for sym,val in sym_r24.tail(5).items():
    print(f"    {sym}: {val:+.4f}%")

# ================================================================
# SIGN TEST per window
# ================================================================
print("\n"+"="*70)
print("SIGN TEST per window")
print("="*70)
def sign_test(n_pos, n_total):
    """Binomial exact two-sided p-value"""
    if n_total==0: return 1.0
    # p = 2 * P(X >= n_pos) under H0: p=0.5
    from math import comb
    p_right=sum(comb(n_total,k) for k in range(n_pos, n_total+1)) / (2**n_total)
    return min(2*p_right, 1.0)

for name,sub in [('TRAIN',dc[dc['split']=='TRAIN']),('VAL',dc[dc['split']=='VAL']),('TEST',dc[dc['split']=='TEST'])]:
    state=sub[sub['STATE']]
    if len(state)==0: continue
    sym_pos=(state.groupby('sym')['R24'].mean()>0).sum()
    sym_tot=len(state.groupby('sym')['R24'].mean())
    pval=sign_test(sym_pos, sym_tot)
    print(f"  {name}: {sym_pos}/{sym_tot} positive, p={pval:.4f} {'***' if pval<0.001 else '**' if pval<0.01 else '*' if pval<0.05 else 'ns'}")

# ================================================================
# CROSS-SYMBOL CONSISTENCY (delta per symbol)
# ================================================================
print("\n"+"="*70)
print("CROSS-SYMBOL CONSISTENCY: delta (state - unconditional) per symbol")
print("="*70)
for name,sub in [('TRAIN',dc[dc['split']=='TRAIN']),('VAL',dc[dc['split']=='VAL']),('TEST',dc[dc['split']=='TEST'])]:
    state=sub[sub['STATE']]
    if len(state)==0: continue
    # Per symbol: state mean vs all mean
    sym_state=state.groupby('sym')['R24'].mean()
    sym_all=sub.groupby('sym')['R24'].mean()
    common=sym_state.index.intersection(sym_all.index)
    delta=(sym_state[common]-sym_all[common])
    pos_d=(delta>0).sum()
    print(f"  {name}: {pos_d}/{len(common)} symbols state>all ({pos_d/len(common)*100:.0f}%), "
          f"median delta={delta.median():+.4f}%, IQR=[{delta.quantile(.25):+.4f},{delta.quantile(.75):+.4f}]")

# ================================================================
# VERDICT
# ================================================================
print("\n"+"="*70)
print("VERDICT — STUDY-005 OOS TEMPORAL SPLIT")
print("="*70)
train_pass=train_r.get('R24',{}).get('mean',0)>0
val_pass=val_r.get('R24',{}).get('mean',0)>0
test_pass=test_r.get('R24',{}).get('mean',0)>0
all_3_pass=train_pass and val_pass and test_pass
trend_monotonic=(train_r.get('R24',{}).get('mean',0)>=val_r.get('R24',{}).get('mean',0)>=test_r.get('R24',{}).get('mean',0))
test_pos=test_r.get('R24',{}).get('pos_sym',0)
test_pct=test_r.get('R24',{}).get('%pos_sym',0)

print(f"  Train PASS (>0): {train_pass} ({train_r.get('R24',{}).get('mean',0):+.4f}%)")
print(f"  Val   PASS (>0): {val_pass} ({val_r.get('R24',{}).get('mean',0):+.4f}%)")
print(f"  Test  PASS (>0): {test_pass} ({test_r.get('R24',{}).get('mean',0):+.4f}%)")
print(f"  All 3 windows positive: {all_3_pass}")
print(f"  Monotonic decay: {trend_monotonic}")
print(f"  Test symbol positive: {test_pos}/{test_r.get('R24',{}).get('n_sym',0)} ({test_pct}%)")
print(f"  Test net(8bps): {test_r.get('net8bps',0):+.1f}bps")

if all_3_pass and test_pass and test_pct>=60:
    verdict="REPRODUCIBLE MARKET EFFECT"
elif all_3_pass:
    verdict="POSITIVE OOS BUT NEEDS REVIEW"
elif test_pass:
    verdict="TEST POSITIVE ONLY"
else:
    verdict="NOT SURVIVED OOS"
print(f"\n  >>> VERDICT: {verdict} <<<")

report={
    'study':'STUDY-005-OOS-VALIDATION','parent':'STUDY-004',
    'state':'FUND_LOW+OI_LOW+HIGH_VOL','frozen':True,
    'split':{'train':'Jul2024-Jun2025','val':'Jul2025-Dec2025','test':'Jan2026-Aug2026'},
    'primary':{
        'train':{'n':train_r['n_state'],'E_R24':train_r.get('R24',{}).get('mean'),'%pos_sym':train_r.get('R24',{}).get('%pos_sym')},
        'val':{'n':val_r['n_state'],'E_R24':val_r.get('R24',{}).get('mean'),'%pos_sym':val_r.get('R24',{}).get('%pos_sym')},
        'test':{'n':test_r['n_state'],'E_R24':test_r.get('R24',{}).get('mean'),'%pos_sym':test_r.get('R24',{}).get('%pos_sym')}},
    'tertiary':{
        'test_pos_sym':test_pos,'test_total_sym':test_r.get('R24',{}).get('n_sym'),
        'test_median':round(float(sym_r24.median()),4) if len(sym_r24)>0 else None,
        'test_IQR':[round(float(sym_r24.quantile(.25)),4),round(float(sym_r24.quantile(.75)),4)] if len(sym_r24)>0 else None},
    'verdict':verdict,
    'label':'OOS Validation — Bukan edge/live. Frozen state, zero optimization.'}
with open(os.path.join(OUT,'STUDY-005_OOS.json'),'w') as f:
    json.dump(report,f,indent=2,default=str)
print(f"\nSaved: research/STUDY-005_OOS.json")
print("STUDY-005 SELESAI")
print("="*70)
