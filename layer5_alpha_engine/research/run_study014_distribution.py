#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-014 — DISTRIBUTION COMPARISON: Apakah 2024 dan 2026 berasal dari
distribusi pasar yang BERBEDA? (bukan mencari alpha, bukan feature mining)

Pertanyaan inti:
  RS directionality berubah reversal→continuation antara 2024 dan 2026.
  Apakah itu karena distribusi pasar (return, dispersion, korelasi, dll)
  sebenarnya BERBEDA antar era?

Metode:
  Statistik non-parametrik (Mann-Whitney U / Kolmogorov-Smirnov) untuk
  membandingkan distribusi:
    - Cross-sectional return dispersion (std ret24 per ts)
    - Cross-sectional RS spread (Q5-Q1)
    - Breadth (% alt ret24>0)
    - Alt average return (mean ret24)
    - Alt skewness
    - Pairwise correlation structure

  Jika distribusi 2024 vs 2026 BERBEDA signifikan → dasar untuk
  hipotesis regime-dependent. Jika TIDAK → RS flips = noise.

  Uji STRICT non-overlap: hanya pakai timestamps berspacing 24h.
"""
import json, os
import pandas as pd, numpy as np

def mannwhitney_u(a,b):
    """Manual Mann-Whitney U (normal approx, no scipy needed)."""
    a=np.asarray(a,dtype=float); b=np.asarray(b,dtype=float)
    n1,n2=len(a),len(b)
    combined=np.concatenate([a,b])
    order=combined.argsort()
    ranks=np.empty_like(order)
    ranks[order]=np.arange(1,len(combined)+1)
    # tie correction
    _,counts=np.unique(combined,return_counts=True)
    tie_correction=(counts**3-counts).sum()
    r1=ranks[:n1].sum()
    u1=n1*n2+n1*(n1+1)/2-r1
    u2=n1*n2-u1
    u=min(u1,u2)
    mu=n1*n2/2
    sigma=np.sqrt(n1*n2*(n1+n2+1-tie_correction/((n1+n2)*(n1+n2-1)))/12)
    if sigma==0: return u,1.0
    z=(u-mu)/sigma
    # two-sided p via normal CDF approximation
    from math import erf,sqrt
    p=2*(1-0.5*(1+erf(abs(z)/sqrt(2))))
    return u,p

def ks_2samp(a,b):
    """Manual 2-sample Kolmogorov-Smirnov (no scipy)."""
    a=np.sort(np.asarray(a,dtype=float)); b=np.sort(np.asarray(b,dtype=float))
    n1,n2=len(a),len(b)
    i=j=0; d=0.0; cdf1=cdf2=0.0
    while i<n1 and j<n2:
        if a[i]<=b[j]:
            cdf1=(i+1)/n1; i+=1
        else:
            cdf2=(j+1)/n2; j+=1
        d=max(d,abs(cdf1-cdf2))
    d=max(d,abs(1-cdf1),abs(1-cdf2))
    # p-value approx (KS two-sided, large sample)
    en=np.sqrt(n1*n2/(n1+n2))
    from math import exp,sqrt,pi
    lam=d*en
    # Kolmogorov distribution approx
    p=2*exp(-2*lam*lam)
    return d,p


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
print("STUDY-014 — DISTRIBUTION COMPARISON 2024 vs 2026")
print("="*70)

frames=[]
for sym in sorted(os.listdir(KDIR)):
    df=load(sym)
    if df is not None: frames.append(df)
all_df=pd.concat(frames,ignore_index=True).sort_values(['sym','ts']).reset_index(drop=True)
ts_count=all_df.groupby('ts').size()
valid=ts_count[ts_count>=10].index
all_df=all_df[all_df['ts'].isin(valid)].dropna(subset=['ret24','R24']).copy()

# Non-overlap: every 24h (global timestamps)
all_df['sym_seq']=all_df.groupby('sym').cumcount()
grid_mask=all_df.groupby('ts')['sym_seq'].transform(lambda s:(s%24==0).all())
all_df=all_df[grid_mask].copy()
all_df['year']=all_df['ts'].dt.year
print(f"Non-overlap grid: {len(all_df)} rows, {all_df['ts'].nunique()} ts")

# Cross-sectional stats per ts
cs=all_df.groupby('ts').agg(
    disp=('ret24','std'),
    skew=('ret24','skew'),
    mean_alt=('ret24','mean'),
    n_sym=('sym','count'),
).reset_index()
breadth=all_df.assign(pos=(all_df['ret24']>0).astype(float)).groupby('ts')['pos'].mean().reset_index()
breadth.columns=['ts','breadth']
cs=cs.merge(breadth,on='ts')
# RS spread per ts
rs=all_df.groupby('ts').apply(lambda d:
    d[d['ret24']==d['ret24'].quantile(0.8)]['R24'].mean() - 0, include_groups=False)
# better: rank-based Q5-Q1 per ts
rs=all_df.groupby('ts').apply(lambda d:
    (d[d['ret24']>=d['ret24'].quantile(0.8)]['R24'].mean()
     - d[d['ret24']<=d['ret24'].quantile(0.2)]['R24'].mean()), include_groups=False)
cs['rs_spread']=rs.values

cs['year']=cs['ts'].dt.year
y24=cs[cs['year']==2024]
y26=cs[cs['year']==2026]

def report(metric, a, b, name):
    if len(a)<10 or len(b)<10:
        print(f"  {metric}: n too small ({len(a)},{len(b)})")
        return
    # Mann-Whitney U (shape/median) + KS (full distribution)
    try:
        u,p_u=mannwhitney_u(a,b)
    except Exception as e:
        p_u=np.nan; u=np.nan
    try:
        ks,p_ks=ks_2samp(a,b)
    except Exception as e:
        p_ks=np.nan; ks=np.nan
    # effect size (Cliff's delta)
    delta=np.mean([1 if x>y else (-1 if x<y else 0) for x in a for y in b]) if len(a)*len(b)<1e6 else np.nan
    print(f"  {metric:<22} 2024={a.mean():+.4f} 2026={b.mean():+.4f} "
          f"| MW_U p={p_u:.4f} KS p={p_ks:.4f} | diff={a.mean()-b.mean():+.4f} "
          f"({'***SIG***' if p_u<0.01 else ('*sig*' if p_u<0.05 else 'ns')})")
    return {'metric':metric,'m24':a.mean(),'m26':b.mean(),'p_mwu':p_u,'p_ks':p_ks}

print("\n" + "="*70)
print("DISTRIBUSI CROSS-SECTIONAL — 2024 (n=%d) vs 2026 (n=%d)"%(len(y24),len(y26)))
print("="*70)
print("  Null: distribusi SAMA (p>0.05) → RS flip = noise")

# Filter to overlapping dates for fair comparison
start_2024=y24['ts'].min(); end_2024=y24['ts'].max()
start_2026=y26['ts'].min(); end_2026=y26['ts'].max()
print(f"  Range 2024: {start_2024} .. {end_2024}")
print(f"  Range 2026: {start_2026} .. {end_2026}")

# Adjust: compare same calendar durations where possible
# Use full-year ranges
results={}
results['dispersion']=report('Dispersion (std)',y24['disp'],y26['disp'],'disp')
results['breadth']=report('Breadth',y24['breadth'],y26['breadth'],'breadth')
results['mean_alt']=report('Alt mean return',y24['mean_alt'],y26['mean_alt'],'mean')
results['skew']=report('Alt skewness',y24['skew'],y26['skew'],'skew')
results['rs_spread']=report('RS spread (Q5-Q1)',y24['rs_spread'],y26['rs_spread'],'rs')

print("\n" + "="*70)
print("INTERPRETASI")
print("="*70)
# Count how many metrics differ significantly
sig=sum(1 for k,v in results.items() if v and v['p_mwu']<0.05)
print(f"  Metrik dgn perbedaan signifikan (p<0.05): {sig}/5")
if sig>=3:
    print("  → 2024 dan 2026 berasal dari DISTRIBUSI BERBEDA.")
    print("  → Dasar statistik untuk hipotesis regime-dependent (bukan noise).")
elif sig>=1:
    print("  → Sebagian metrik berbeda, sebagian tidak. MIXED evidence.")
    print("  → RS directionality mungkin sebagian regime, sebagian noise.")
else:
    print("  → Tidak ada perbedaan signifikan antar era.")
    print("  → RS directionality KEMUNGKINAN BESAR noise (bukan regime).")

report={'study':'STUDY-014','n2024':len(y24),'n2026':len(y26),'metrics':results}
with open(os.path.join(OUT,'STUDY-014_DISTRIBUTION.json'),'w') as f:
    json.dump(report,f,indent=2,default=str)
print(f"\nSaved: research/STUDY-014_DISTRIBUTION.json")
print("="*70)