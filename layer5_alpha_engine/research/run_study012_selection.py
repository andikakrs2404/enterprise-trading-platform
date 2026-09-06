#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-012 — SELECTION (Portfolio Construction, Pertanyaan 1 dari 3)
====================================================================
PREREGISTERED (STUDY-012_PREREGISTRATION.md):
  Baseline: equal-weight universe (long-only)
  Selection: equal-weight top-Q5 Price RS (long-only) + Q5L-Q1S spread
  Horizon: R24, rebalance setiap 24 bar (align effect horizon — postmortem 007)
  Non-overlap sample sejak awal (aturan STUDY-008)
  Cost: 8/12/16 bps, turnover EKSPLISIT
  Split: TRAIN/VAL/TEST per timeline (60/20/20)

Pertanyaan: apakah memilih Q5 RS konsisten lebih baik dari equal-weight universe?
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
print("STUDY-012 — SELECTION: Q5 RS vs equal-weight universe")
print("="*70)

frames=[]
for sym in sorted(os.listdir(KDIR)):
    df=load(sym)
    if df is not None: frames.append(df)
all_df=pd.concat(frames,ignore_index=True).sort_values('ts').reset_index(drop=True)
ts_count=all_df.groupby('ts').size()
valid=ts_count[ts_count>=10].index
all_df=all_df[all_df['ts'].isin(valid)].dropna(subset=['ret24','R24']).copy()
all_df['year']=all_df['ts'].dt.year

# Cross-sectional RS rank per timestamp (frozen STUDY-006)
all_df['rs_rank']=all_df.groupby('ts')['ret24'].rank(pct=True)
all_df['rs_q']=pd.qcut(all_df['rs_rank'],5,labels=False,duplicates='drop')
# Q5 = top 20%, Q1 = bottom 20%

# ---- NON-OVERLAP rebalance grid: every 24th bar of global timeline ----
# per symbol sequence for clean non-overlap
all_df=all_df.sort_values(['sym','ts']).reset_index(drop=True)
all_df['sym_seq']=all_df.groupby('sym').cumcount()
# Use timestamps where ALL symbols have seq % 24 == 0 → truly aligned non-overlap
# (simpler: take per-timestamp, keep ts where every present symbol is on grid)
grid_mask=all_df.groupby('ts')['sym_seq'].transform(lambda s:(s%24==0).all())
dc=all_df[grid_mask].copy()
print(f"Non-overlap rebalance periods: {dc['ts'].nunique()} timestamps, "
      f"{len(dc)} rows, {dc['sym'].nunique()} sym")

# ---- Portfolio returns per rebalance timestamp ----
def port_ret(d, kind):
    """kind: 'universe' (all), 'Q5' (top), 'Q1' (bottom), 'Q5L_Q1S' (spread)"""
    if kind=='universe':
        return d['R24'].mean()
    if kind=='Q5':
        s=d[d['rs_q']==4]
        return s['R24'].mean() if len(s)>0 else np.nan
    if kind=='Q1':
        s=d[d['rs_q']==0]
        return s['R24'].mean() if len(s)>0 else np.nan
    if kind=='Q5L_Q1S':
        s5=d[d['rs_q']==4]['R24'].mean()
        s1=d[d['rs_q']==0]['R24'].mean()
        return s5-s1 if (not np.isnan(s5) and not np.isnan(s1)) else np.nan

results=[]
for ts, d in dc.groupby('ts'):
    results.append({
        'ts':ts,
        'universe':port_ret(d,'universe'),
        'q5':port_ret(d,'Q5'),
        'q1':port_ret(d,'Q1'),
        'q5_q1':port_ret(d,'Q5L_Q1S'),
    })
pf=pd.DataFrame(results).dropna().sort_values('ts').reset_index(drop=True)
print(f"Portfolio periods: {len(pf)}")

# ---- Turnover: fraction of Q5 selection changing between rebalances ----
# Q5 membership at each ts
membership={}
for ts,d in dc.groupby('ts'):
    mem=set(d[d['rs_q']==4]['sym'])
    for q1_mem in [False,True]:
        membership[(ts,q1_mem)]=mem if not q1_mem else set(d[d['rs_q']==0]['sym'])
# simplify: membership for Q5 only
mem_by_ts={ts:set(d[d['rs_q']==4]['sym']) for ts,d in dc.groupby('ts')}
ts_list=sorted(mem_by_ts.keys())
turnover=[]
for i in range(1,len(ts_list)):
    prev=mem_by_ts[ts_list[i-1]]; cur=mem_by_ts[ts_list[i]]
    # fraction of value traded: sym leaving + sym entering, each weighted 1/|prev|
    n=len(prev)
    if n>0:
        traded=(len(prev-cur)+len(cur-prev))/n
        turnover.append(traded)
pf['turnover']=np.nan
for i,t in enumerate(ts_list[1:],start=1):
    pf.loc[pf['ts']==t,'turnover']=turnover[i-1]
# first period turnover = full entry (1.0) for Q5; universe ~0
pf['turnover']=pf['turnover'].fillna(1.0)

# ---- Splits (60/20/20) ----
pf['split']=''
n=len(pf)
pf.loc[:int(n*0.6),'split']='train'
pf.loc[int(n*0.6):int(n*0.8),'split']='val'
pf.loc[int(n*0.8):,'split']='test'

def net_of(row, gross_col, fee_bps):
    return row[gross_col]-row['turnover']*fee_bps/100

def metrics(sub, col, fee, name):
    g=sub[col]
    to=sub['turnover'].mean()
    net=g.mean()-to*fee/100
    hit=(g>0).mean()*100
    sharpe=g.mean()/g.std()*np.sqrt(365/ (24/24)) if g.std()>0 else np.nan  # annualized-ish per day
    return {'name':name,'gross_bps':g.mean()*100,'net_bps':net*100,
            'hit%':hit,'turnover':to,'n':len(g)}

print("\n"+"="*70)
print("HASIL — per split, per portfolio (net setelah turnover×fee)")
print("="*70)
for split_name in ['train','val','test']:
    sub=pf[pf['split']==split_name]
    print(f"\n  --- {split_name.upper()} ({len(sub)} periods) ---")
    print(f"  {'Strategi':<18}{'gross(bps)':>10}{'to':>7}{'net8':>8}{'net12':>8}{'net16':>8}{'hit%':>7}")
    for col,label in [('universe','Universe EW'),('q5','Q5 select EW'),('q5_q1','Q5L-Q1S')]:
        g=sub[col].mean()*100
        to=sub['turnover'].mean() if col!='universe' else 0.02
        if col=='universe': to=0.01  # ~no turnover, drift only
        if col=='q5_q1': to=sub['turnover'].mean()*2  # both sides
        net8=g-to*8/100*100
        net12=g-to*12
        net16=g-to*16
        hit=(sub[col]>0).mean()*100
        print(f"  {label:<18}{g:>10.2f}{to:>7.2f}{net8:>8.2f}{net12:>8.2f}{net16:>8.2f}{hit:>6.0f}%")

# ---- Breadth: % symbols where being in Q5 beats universe mean ----
print("\n"+"="*70)
print("BREADTH — % simbol di mana R24 (saat Q5) > mean universe")
print("="*70)
for split_name in ['train','val','test']:
    sub=dc[dc['ts'].isin(pf[pf['split']==split_name]['ts'])]
    cnt=0; win=0
    for sym,sd in sub.groupby('sym'):
        cnt+=1
        s5=sd[sd['rs_q']==4]['R24']
        univ=sd['R24'].mean()
        if len(s5)>0 and s5.mean()>univ: win+=1
    print(f"  {split_name}: {win}/{cnt} ({win/cnt*100:.0f}%)")

# ---- Per-symbol consistency ----
print("\n"+"="*70)
print("PER-SYMBOL: mean R24 saat Q5 vs saat bukan Q5")
print("="*70)
rows=[]
for sym,sd in dc.groupby('sym'):
    q5=sd[sd['rs_q']==4]['R24'].mean()
    nq5=sd[sd['rs_q']!=4]['R24'].mean()
    rows.append({'sym':sym,'q5':q5,'not_q5':nq5,'delta':q5-nq5})
ps=pd.DataFrame(rows)
pos=(ps['delta']>0).sum(); neg=(ps['delta']<0).sum()
print(f"  Simbol dgn Q5>nonQ5: {pos}/{len(ps)} ({pos/len(ps)*100:.0f}%)")
print(f"  Mean delta: {ps['delta'].mean():+.4f}%")

# ================================================================
# VERDICT SELECTION (per failure criteria STUDY-012)
# ================================================================
print("\n"+"="*70)
print("VERDICT — SELECTION")
print("="*70)
test=pf[pf['split']=='test']
univ_test=test['universe'].mean()*100
q5_test=test['q5'].mean()*100
q5_net12=q5_test-test['turnover'].mean()*12
# criterion A: Q5 net > universe net?
print(f"  TEST: universe gross={univ_test:+.2f}bps | Q5 gross={q5_test:+.2f}bps | Q5 net@12={q5_net12:+.2f}bps")
# consistency
for s in ['train','val','test']:
    sub=pf[pf['split']==s]
    print(f"  {s}: Q5 gross={sub['q5'].mean()*100:+.2f}bps vs universe {sub['universe'].mean()*100:+.2f}bps")

report={
 'study':'STUDY-012-SELECTION','phase':'portfolio-construction',
 'baseline':'equal-weight universe','selection':'top-Q5 Price RS EW',
 'horizon':'R24','non_overlap':'every 24 bar','fee':[8,12,16],
 'verdict_note':'Selection question — subset of STUDY-012'}
with open(os.path.join(OUT,'STUDY-012_SELECTION.json'),'w') as f:
    json.dump(report,f,indent=2,default=str)
print("\nSaved: research/STUDY-012_SELECTION.json")
print("="*70)