#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-013B — DEFINITION ROBUSTNESS VALIDATION
================================================
Status: VALIDATION dari STUDY-013 (SUPPORTED, NOT VALIDATED)

Hipotesis yang diuji (DIBEKUKAN):
  RS bekerja lebih baik ketika market breadth/trend positif.

TIDAK BOLEH:
  - Menambah fitur baru
  - Mengubah narasi
  - Optimasi threshold

3 TUJUAN (saja):
  1. Threshold robustness: 50/60/70/80 percentile → sign harus konsisten
  2. Lag robustness: 12/24/48h → sign harus konsisten
  3. Real-time implementability: rolling percentile (window 168h) → sign harus konsisten

EVALUASI:
  Bukan mencari magnitude terbaik.
  Tapi mencari KONSISTENSI TANDA lintas definisi.
  Jika hanya hidup di 1 threshold: boundary artifact → REJECT.
  Jika hidup di semua: robust → VALIDATE.
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
    df['ret24']=df['close'].pct_change(24)
    df['R24']=(df['close'].shift(-24)/df['close']-1)*100
    df['sym']=sym
    return df

print("="*70)
print("STUDY-013B — DEFINITION ROBUSTNESS VALIDATION")
print("="*70)

frames=[]
for sym in sorted(os.listdir(KDIR)):
    df=load(sym)
    if df is not None: frames.append(df)
all_df=pd.concat(frames,ignore_index=True).sort_values(['sym','ts']).reset_index(drop=True)
ts_count=all_df.groupby('ts').size()
valid=ts_count[ts_count>=10].index
all_df=all_df[all_df['ts'].isin(valid)].dropna(subset=['ret24','R24']).copy()
all_df['rs_rank']=all_df.groupby('ts')['ret24'].rank(pct=True)
all_df['year']=all_df['ts'].dt.year

# Alt-only for market states
ms=all_df[~all_df['sym'].isin(['BTCUSDT','ETHUSDT'])].copy()
ts_state=ms.groupby('ts').agg(
    ret24_all=('ret24','mean'),
    ret24_std=('ret24','std'),
).reset_index()
breadth=ms.assign(pos=(ms['ret24']>0).astype(float)).groupby('ts')['pos'].mean().reset_index()
breadth.columns=['ts','breadth']
ts_state=ts_state.merge(breadth,on='ts').sort_values('ts').reset_index(drop=True)

# Splits (from all_df global)
ts_all=all_df.groupby('ts').size()
valid_split=ts_all[ts_all>=10].index
split_ts=pd.DataFrame({'ts':sorted(valid_split)})
n=len(split_ts)
split_ts['split']=''
split_ts.loc[:int(n*0.6),'split']='train'
split_ts.loc[int(n*0.6):int(n*0.8),'split']='val'
split_ts.loc[int(n*0.8):,'split']='test'
split_map=dict(zip(split_ts['ts'],split_ts['split']))

def rs_spread(sub_ts_set):
    d=all_df[all_df['ts'].isin(sub_ts_set)]
    q5=d[d['rs_rank']>0.8]['R24'].mean()*100
    q1=d[d['rs_rank']<0.2]['R24'].mean()*100
    return q5-q1

def all_splits(ts_set):
    results={}
    for s in ['train','val','test']:
        sub=[t for t in ts_set if split_map.get(t,'')=='s']
        results[s]=rs_spread(sub) if sub else np.nan
    results['ALL']=rs_spread(ts_set)
    return results

# ================================================================
# 1. THRESHOLD ROBUSTNESS (breadth & trend, 50/60/70/80 pctl)
# ================================================================
print("\n" + "="*70)
print("1. THRESHOLD ROBUSTNESS — breadth & trend at 50/60/70/80 percentile")
print("="*70)
print(f"  {'State':<10}{'Pctl':>5}{'n_hi':>6}{'ALL':>8}{'TRAIN':>8}{'VAL':>8}{'TEST':>8}{'sign_ok':>8}")

for state_name, col, pcts in [
    ('Breadth','breadth',[50,60,70,80]),
    ('Trend','ret24_all',[50,60,70,80]),
]:
    for p in pcts:
        thresh=np.percentile(ts_state[col].dropna(),p)
        hi=set(ts_state[ts_state[col]>=thresh]['ts'])
        sp=rs_spread(hi)
        splits={}
        for s in ['train','val','test']:
            sub=[t for t in hi if split_map.get(t,'')==s]
            splits[s]=rs_spread(sub) if sub else np.nan
        sign_ok = all(v>0 for v in [sp, splits['train'], splits['val'], splits['test']] if not np.isnan(v))
        print(f"  {state_name:<10}{p:>4}%{len(hi):>6}{sp:>+8.2f}{splits['train']:>+8.2f}{splits['val']:>+8.2f}{splits['test']:>+8.2f}{'  ✓' if sign_ok else '  ✗'}")

# ================================================================
# 2. LAG ROBUSTNESS (12h/24h/48h)
# ================================================================
print("\n" + "="*70)
print("2. LAG ROBUSTNESS — breadth & trend at lag 12/24/48h (median split)")
print("="*70)
print(f"  {'State':<10}{'Lag':>5}{'n_hi':>6}{'ALL':>8}{'TRAIN':>8}{'VAL':>8}{'TEST':>8}{'sign_ok':>8}")

# Compute lags
ts_state_s=ts_state.sort_values('ts').set_index('ts')
for lag_h in [12,24,48]:
    ts_state_s[f'breadth_lag{lag_h}']=ts_state_s['breadth'].shift(lag_h)
    ts_state_s[f'trend_lag{lag_h}']=ts_state_s['ret24_all'].shift(lag_h)
ts_state_s=ts_state_s.dropna(subset=[f'breadth_lag{h}' for h in [12,24,48]]+[f'trend_lag{h}' for h in [12,24,48]])
ts_state_s=ts_state_s.reset_index()

for state_name, lag_prefix in [('Breadth','breadth'),('Trend','trend')]:
    for lag_h in [12,24,48]:
        col=f'{lag_prefix}_lag{lag_h}'
        med=np.median(ts_state_s[col].dropna())
        hi=set(ts_state_s[ts_state_s[col]>=med]['ts'])
        sp=rs_spread(hi)
        splits={}
        for s in ['train','val','test']:
            sub=[t for t in hi if split_map.get(t,'')==s]
            splits[s]=rs_spread(sub) if sub else np.nan
        sign_ok = all(v>0 for v in [sp, splits['train'], splits['val'], splits['test']] if not np.isnan(v))
        print(f"  {state_name:<10}{lag_h:>4}h{len(hi):>6}{sp:>+8.2f}{splits['train']:>+8.2f}{splits['val']:>+8.2f}{splits['test']:>+8.2f}{'  ✓' if sign_ok else '  ✗'}")

# ================================================================
# 3. REAL-TIME IMPLEMENTABILITY (rolling percentile, window 168h = 7 days)
# ================================================================
print("\n" + "="*70)
print("3. ROLLING PERCENTILE (window 168h) — real-time implementable")
print("="*70)

# Compute rolling percentiles (168h = 7 days)
ts_state_r=ts_state.sort_values('ts').copy()
ts_state_r['breadth_roll_pctl']=ts_state_r['breadth'].rolling(168,min_periods=84).apply(
    lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False)
ts_state_r['trend_roll_pctl']=ts_state_r['ret24_all'].rolling(168,min_periods=84).apply(
    lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False)
ts_state_r=ts_state_r.dropna(subset=['breadth_roll_pctl','trend_roll_pctl'])

# Split
ts_state_r=ts_state_r.copy()
n_r=len(ts_state_r)
ts_state_r['split']=''
ts_state_r.loc[:int(n_r*0.6),'split']='train'
ts_state_r.loc[int(n_r*0.6):int(n_r*0.8),'split']='val'
ts_state_r.loc[int(n_r*0.8):,'split']='test'
# Map for quick lookup
split_map_r=dict(zip(ts_state_r['ts'],ts_state_r['split']))

print(f"  {'State':<10}{'Method':<12}{'n_hi':>6}{'ALL':>8}{'TRAIN':>8}{'VAL':>8}{'TEST':>8}{'sign_ok':>8}")

for state_name, col in [('Breadth','breadth_roll_pctl'),('Trend','trend_roll_pctl')]:
    hi=set(ts_state_r[ts_state_r[col]>=0.5]['ts'])
    sp=rs_spread(hi)
    splits={}
    for s in ['train','val','test']:
        sub=[t for t in hi if split_map_r.get(t,'')==s]
        splits[s]=rs_spread(sub) if sub else np.nan
    sign_ok = all(v>0 for v in [sp, splits['train'], splits['val'], splits['test']] if not np.isnan(v))
    print(f"  {state_name:<10}{'rolling≥50%':<12}{len(hi):>6}{sp:>+8.2f}{splits['train']:>+8.2f}{splits['val']:>+8.2f}{splits['test']:>+8.2f}{'  ✓' if sign_ok else '  ✗'}")

# ================================================================
# SUMMARY TABLE
# ================================================================
print("\n" + "="*70)
print("SUMMARY — sign consistency across ALL definitions")
print("="*70)

# Breadth thresholds
breadth_signs=[]
for p in [50,60,70,80]:
    thresh=np.percentile(ts_state['breadth'].dropna(),p)
    hi=set(ts_state[ts_state['breadth']>=thresh]['ts'])
    sp=rs_spread(hi)
    breadth_signs.append(('Breadth',f'{p}th',sp,sp>0))
trend_signs=[]
for p in [50,60,70,80]:
    thresh=np.percentile(ts_state['ret24_all'].dropna(),p)
    hi=set(ts_state[ts_state['ret24_all']>=thresh]['ts'])
    sp=rs_spread(hi)
    trend_signs.append(('Trend',f'{p}th',sp,sp>0))
# Breadth lags
breadth_lag_signs=[]
for lag in [12,24,48]:
    col=f'breadth_lag{lag}'
    med=np.median(ts_state_s[col].dropna())
    hi=set(ts_state_s[ts_state_s[col]>=med]['ts'])
    sp=rs_spread(hi)
    breadth_lag_signs.append(('Breadth',f'{lag}h',sp,sp>0))
trend_lag_signs=[]
for lag in [12,24,48]:
    col=f'trend_lag{lag}'
    med=np.median(ts_state_s[col].dropna())
    hi=set(ts_state_s[ts_state_s[col]>=med]['ts'])
    sp=rs_spread(hi)
    trend_lag_signs.append(('Trend',f'{lag}h',sp,sp>0))

print(f"\n  {'State':<10}{'Def':<10}{'spread':>10}{'sign':>6}")
print(f"  {'-'*40}")
for row in breadth_signs+trend_signs+breadth_lag_signs+trend_lag_signs:
    print(f"  {row[0]:<10}{row[1]:<10}{row[2]:>+10.2f}{'  ✓' if row[3] else '  ✗'}")

# Count
all_signs=[r[3] for r in breadth_signs+trend_signs+breadth_lag_signs+trend_lag_signs]
n_pos=sum(all_signs); n_total=len(all_signs)
print(f"\n  Total positive: {n_pos}/{n_total} ({n_pos/n_total*100:.0f}%)")

report={
    'study':'STUDY-013B',
    'threshold_robustness':'50/60/70/80 pctl',
    'lag_robustness':'12/24/48h',
    'rolling_implementability':'168h window',
    'sign_consistency':f'{n_pos}/{n_total}',
}
with open(os.path.join(OUT,'STUDY-013B_ROBUSTNESS.json'),'w') as f:
    json.dump(report,f,indent=2,default=str)
print(f"\nSaved: research/STUDY-013B_ROBUSTNESS.json")
print("="*70)