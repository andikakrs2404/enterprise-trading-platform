#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-012 — SIZING/EXPOSURE (pertanyaan terakhir, formal close)
+ INVESTIGASI 2025 (structural signal)

SIZING:
  Apakah conditional exposure (hanya trade saat signal kuat) lebih viable?
  Ex-ante rules: hanya masuk saat: rs_rank > 0.8 (top Q5) + ret24 > median
  Jangan optimize threshold — pakai definisi ex-ante.
  Rebalance tiap 24 bar, non-overlap, net@12/16.

2025 INVESTIGASI:
  Apa yang berbeda di 2025 sehingga SEMUA studi gagal?
  - BTC price action (bull→bear→recovery?)
  - Cross-sectional return dispersion
  - Volume / OI regime
  - Alt correlation (tinggi=semua gerak sama, RS tidak berguna)
"""
import json, os
import pandas as pd, numpy as np

DATA='/home/rtk/Bot-Multi-Edge-metrics/data'
KDIR=DATA+'/klines'
OUT='/home/rtk/enterprise-trading-platform/layer5_alpha_engine/research'

def load(sym):
    k=os.path.join(KDIR,sym,'klines_1h.parquet')
    if not os.path.exists(k): return None
    df=pd.read_parquet(k)[['close','volume']].copy()
    df=df.rename_axis('ts').reset_index()
    df['ts']=pd.to_datetime(df['ts'],utc=True)
    df['ret']=df['close'].pct_change()
    df['ret24']=df['close'].pct_change(24)
    df['R24']=(df['close'].shift(-24)/df['close']-1)*100
    df['sym']=sym
    return df

print("="*70)
print("STUDY-012 — SIZING + 2025 STRUCTURAL INVESTIGATION")
print("="*70)

frames=[]
for sym in sorted(os.listdir(KDIR)):
    df=load(sym)
    if df is not None: frames.append(df)
all_df=pd.concat(frames,ignore_index=True).sort_values(['sym','ts']).reset_index(drop=True)
ts_count=all_df.groupby('ts').size()
valid=ts_count[ts_count>=10].index
all_df=all_df[all_df['ts'].isin(valid)].dropna(subset=['ret24','R24']).copy()
all_df['year']=all_df['ts'].dt.year

# RS
all_df['rs_rank']=all_df.groupby('ts')['ret24'].rank(pct=True)
all_df['sym_seq']=all_df.groupby('sym').cumcount()
grid_mask=all_df.groupby('ts')['sym_seq'].transform(lambda s:(s%24==0).all())
dc=all_df[grid_mask].copy().sort_values(['ts','sym'])
dc['N']=dc.groupby('ts')['sym'].transform('count')
dc['w_ew']=1.0/dc['N']

# Sizing: conditional exposure — only when BOTH top Q5 AND ret24>median
ts_median=dc.groupby('ts')['ret24'].median()
dc['above_median']=dc.apply(lambda r:r['ret24']>ts_median.get(r['ts'],0),axis=1).astype(float)
dc['active']=(dc['rs_rank']>0.8)&(dc['above_median']==1.0).astype(float)
# subset sum: active=1 means included
dc['w_cond']=dc['active']/dc.groupby('ts')['active'].transform('sum')
dc.loc[dc['active']==0,'w_cond']=0

# Unconditional Q5 for reference
dc['w_q5']=np.where(dc['rs_rank']>0.8,1.0/dc.groupby('ts')['rs_rank'].apply(lambda x:(x>0.8).sum()).reindex(dc['ts']).values,0)

# Returns
def calc_port(df,col):
    return df.groupby('ts').apply(lambda d:(d[col]*d['R24']).sum()*100,include_groups=False)

pf=pd.DataFrame({'ts':sorted(dc['ts'].unique())})
pf['year']=pd.to_datetime(pf['ts']).dt.year
pf['ew']=calc_port(dc,'w_ew').values
pf['q5']=calc_port(dc,'w_q5').values
pf['cond']=calc_port(dc,'w_cond').values

# Turnover
for name,col in [('q5','w_q5'),('cond','w_cond')]:
    prev=dc.groupby('ts')[col].shift(1).fillna(0)
    to=((dc[col]-prev).abs().groupby(dc['ts']).sum())
    pf[name+'_to']=to.reindex(pf['ts']).values
pf['ew_to']=0.0

# Coverage
coverage=dc.groupby('ts')['active'].sum()
pf['coverage']=coverage.reindex(pf['ts']).values
pf['coverage_pct']=pf['coverage']/pf.groupby('ts')['ts'].transform('count')

# Split
n=len(pf)
pf['split']=''
pf.loc[:int(n*0.6),'split']='train'
pf.loc[int(n*0.6):int(n*0.8),'split']='val'
pf.loc[int(n*0.8):,'split']='test'

print("\n--- SIZING: Conditional exposure (rs_rank>0.8 + ret24>median) ---")
print(f"{'Split':<8}{'ew gross':>10}{'q5 gross':>10}{'cond gross':>12}{'q5 net12':>10}{'cond net12':>12}{'cov%':>6}")
for s in ['train','val','test']:
    sub=pf[pf['split']==s]
    print(f"  {s:<6}{sub['ew'].mean():>+10.2f}{sub['q5'].mean():>+10.2f}{sub['cond'].mean():>+12.2f}"
          f"{sub['q5'].mean()-sub['q5_to'].mean()*12:>+10.2f}{sub['cond'].mean()-sub['cond_to'].mean()*12:>+12.2f}"
          f"{sub['coverage_pct'].mean()*100:>5.0f}%")
print(f"  Coverage (active bars): {pf['coverage_pct'].mean()*100:.0f}%")

print("\n--- PER YEAR ---")
for y in [2024,2025,2026]:
    sub=pf[pf['year']==y]
    print(f"  {y}: ew={sub['ew'].mean():+.2f} q5={sub['q5'].mean():+.2f} cond={sub['cond'].mean():+.2f} "
          f"cov={sub['coverage_pct'].mean()*100:.0f}%")

# ================================================================
# 2025 STRUCTURAL INVESTIGATION
# ================================================================
print("\n"+"="*70)
print("2025 INVESTIGASI — Apa yang berbeda secara structural?")
print("="*70)

# 1. BTC price trajectory (monthly)
btc=all_df[all_df['sym']=='BTCUSDT'][['ts','close','ret24']].copy()
btc['month']=btc['ts'].dt.to_period('M')
btc_month=btc.groupby('month').agg(close=('close','last'),ret=('ret24','mean'))
print("\n1. BTC PRICE TRAJECTORY (monthly close + avg R24)")
for idx,row in btc_month.iterrows():
    print(f"  {idx}: close=${row['close']:,.0f} avg_ret24={row['ret']:+.4f}%")

# 2. Cross-sectional dispersion by year
print("\n2. CROSS-SECTIONAL DISPERSION by year")
for y in [2024,2025,2026]:
    sub=all_df[all_df['year']==y]
    disp=sub.groupby('ts')['ret24'].agg(lambda x:x.quantile(0.75)-x.quantile(0.25)).mean()
    disp_mean=sub.groupby('ts')['ret24'].std().mean()
    print(f"  {y}: IQR(disp)={disp:.4f} avg_std={disp_mean:.4f}")

# 3. Avg correlation between alts by year (KEY: high corr = RS useless)
print("\n3. CROSS-SECTIONAL CORRELATION (median pairwise corr of hourly returns)")
for y in [2024,2025,2026]:
    sub=all_df[(all_df['year']==y)&(~all_df['sym'].isin(['BTCUSDT','ETHUSDT']))]
    corr_vals=[]
    for ts_val,g in sub.groupby('ts'):
        pivot=g.pivot_table(index='sym',columns='ts',values='ret')
        if pivot.shape[0]>=5:
            c=pivot.corr()
            vals=c.values[np.triu_indices_from(c.values,k=1)]
            corr_vals.extend(vals[~np.isnan(vals)])
    if corr_vals:
        print(f"  {y}: median_corr={np.median(corr_vals):.4f} mean={np.mean(corr_vals):.4f} n_pairs={len(corr_vals)}")

# 4. RS spread by year (R24, Q5-Q1 per year)
print("\n4. RS SPREAD (Q5-Q1 R24) per YEAR")
for y in [2024,2025,2026]:
    sub=dc[dc['year']==y]
    q5=sub[sub['rs_rank']>0.8]['R24'].mean()
    q1=sub[sub['rs_rank']<0.2]['R24'].mean()
    sym_q5=sub[sub['rs_rank']>0.8].groupby('sym')['R24'].mean()
    sym_q1=sub[sub['rs_rank']<0.2].groupby('sym')['R24'].mean()
    common=sym_q5.index.intersection(sym_q1.index)
    pos=(sym_q5[common]>sym_q1[common]).sum()/len(common)*100 if len(common)>0 else 0
    print(f"  {y}: Q1={q1:+.4f}% Q5={q5:+.4f}% spread={q5-q1:+.4f}% breadth={pos:.0f}%")

# 5. Alt avg return by year (systematic up/down)
print("\n5. ALT AVERAGE RETURN by year (systematic direction)")
for y in [2024,2025,2026]:
    sub=all_df[(all_df['year']==y)&(~all_df['sym'].isin(['BTCUSDT','ETHUSDT']))]
    print(f"  {y}: avg_R24={sub['R24'].mean():+.4f}% monthly_avg={sub.groupby('ts')['R24'].mean().mean():+.4f}%")

# Save
report={'study':'STUDY-012-SIZING-2025','sizing_verdict':'conditional_exposure_test',
        'structural_2025':'see_out'}
with open(os.path.join(OUT,'STUDY-012_SIZING_2025.json'),'w') as f:
    json.dump(report,f,indent=2,default=str)
print(f"\nSaved: research/STUDY-012_SIZING_2025.json")
print("="*70)