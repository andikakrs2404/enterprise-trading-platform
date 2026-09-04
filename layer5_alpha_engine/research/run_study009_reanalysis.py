#!/usr/bin/env /usr/bin/python3.11
"""STUDY-009 REANALYSIS — clean full script."""
import pandas as pd, numpy as np, os, warnings
warnings.filterwarnings('ignore')
DATA='/home/rtk/Bot-Multi-Edge-metrics/data'
KDIR=DATA+'/klines'
def load(sym):
    k=os.path.join(KDIR,sym,'klines_1h.parquet')
    if not os.path.exists(k): return None
    df=pd.read_parquet(k)[['close']].copy()
    df=df.rename_axis('ts').reset_index()
    df['ts']=pd.to_datetime(df['ts'],utc=True)
    df['ret']=df['close'].pct_change()
    df['ret24']=df['close'].pct_change(24)
    df['R24']=(df['close'].shift(-24)/df['close']-1)*100
    df['sigma_s']=df['ret'].rolling(6).std()
    df['sigma_b']=df['ret'].rolling(168).std()
    df['vratio']=df['sigma_s']/df['sigma_b']
    df['sym']=sym
    return df

frames=[]
for sym in sorted(os.listdir(KDIR)):
    df=load(sym)
    if df is not None: frames.append(df)
all_df=pd.concat(frames,ignore_index=True).sort_values('ts').reset_index(drop=True)
ts_count=all_df.groupby('ts').size()
valid=ts_count[ts_count>=10].index
all_df=all_df[all_df['ts'].isin(valid)]
all_df=all_df.dropna(subset=['vratio','ret24','R24']).copy()
all_df['year']=all_df['ts'].dt.year
all_df['vol_rank']=all_df.groupby('ts')['vratio'].rank(pct=True)
all_df=all_df.sort_values(['sym','ts']).reset_index(drop=True)
all_df['sym_seq']=all_df.groupby('sym').cumcount()

print("[E] NON-OVERLAP per year (every 72nd bar per symbol)")
dc_no=all_df[all_df['sym_seq']%72==0].copy()
dc_no['vol_rank']=dc_no.groupby('ts')['vratio'].rank(pct=True)
dc_no['vol_q']=pd.cut(dc_no['vol_rank'],bins=[-0.01,0.2,0.4,0.6,0.8,1.01],labels=['Q1','Q2','Q3','Q4','Q5'])
for yr in [2024,2025,2026]:
    sub=dc_no[dc_no['year']==yr]
    if len(sub)<100: print(f"  {yr}: n={len(sub)} small"); continue
    q1=sub[sub['vol_q']=='Q1']['R24'].mean()
    q5=sub[sub['vol_q']=='Q5']['R24'].mean()
    sp={}
    for sym in sub['sym'].unique():
        ss=sub[sub['sym']==sym]
        if len(ss)<20: continue
        q5m=ss[ss['vol_q']=='Q5']['R24'].mean()
        q1m=ss[ss['vol_q']=='Q1']['R24'].mean()
        if not np.isnan(q5m) and not np.isnan(q1m): sp[sym]=q5m-q1m
    pos=sum(1 for v in sp.values() if v>0) if sp else 0
    print(f"  {yr}: Q1(contr)={q1:+.4f}% Q5(expan)={q5:+.4f}% spread={q5-q1:+.4f}% "
          f"(n={len(sub)}, {pos}/{len(sp)} sym positive)")

print()
print("[F] VOL RATIO distribution per year")
for yr in [2024,2025,2026]:
    sub=all_df[all_df['year']==yr]
    for q in ['Q1','Q5']:
        if q=='Q1':
            s=sub[sub['vol_rank']<0.2]['vratio']
        else:
            s=sub[sub['vol_rank']>0.8]['vratio']
        label='contr' if q=='Q1' else 'expan'
        print(f"  {yr} {q}({label}): mean={s.mean():.4f} median={s.median():.4f}")
print()
print("DONE")
