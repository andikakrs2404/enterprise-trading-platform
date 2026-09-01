#!/usr/bin/env /usr/bin/python3.11
"""
P1.7 ANTI-DATA-SNOOPING: Temporal Split + Multiple Testing + ADX Curve
======================================================================
Urutan (sesuai arahan user):
1. Perbaiki temporal split: per-symbol 2024-07->2025-07 TRAIN,
   2025-07->2026-01 VAL, 2026-01->2026-08 TEST, gabung setelah split.
2. Multiple-testing correction (p_bonferroni, p_holm, p_fdr) utk SEMUA
   eksplorasi ADX bucket.
3. ADX curve/percentile kontinu (P10..P90) - bukan hanya bucket.
4. Freeze ADX sweet-spot -> OOS validation di window 2026.
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
        df['oi_change_pct']=df['sum_open_interest'].pct_change()*100
    else:
        df['oi_change_pct']=np.nan
    if os.path.exists(f):
        fund=pd.read_parquet(f); fund.index=pd.to_datetime(fund.index,utc=True)
        df=df.join(fund[['funding_rate']],how='left')
    else:
        df['funding_rate']=np.nan
    return df

def vec_features(df, period=14):
    o=df['open'].values;h=df['high'].values;l=df['low'].values;c=df['close'].values;v=df['volume'].values
    hl=h-l;hc=np.abs(h-np.roll(c,1));hc[0]=0;lc=np.abs(l-np.roll(c,1));lc[0]=0
    tr=np.maximum(hl,np.maximum(hc,lc))
    atr=pd.Series(tr).rolling(period).mean().values
    atr100=pd.Series(tr).rolling(100).mean().values
    atr100=np.where(np.isnan(atr100),atr,atr100)
    atr_ratio=np.where(atr100>0,atr/atr100,1.0)
    closes=pd.Series(c)
    sma20=closes.rolling(20).mean();std20=closes.rolling(20).std()
    bb_arr=np.where((sma20>0).values,(4*std20/sma20).values,0.0)
    vol_sma=pd.Series(v).rolling(20).mean()
    vr_arr=np.where((vol_sma>0).values,(v/vol_sma).values,1.0)
    up=h-np.roll(h,1);up[0]=0;dn=np.roll(l,1)-l;dn[0]=0
    pdm=np.where((up>dn)&(up>0),up,0.0);mdm=np.where((dn>up)&(dn>0),dn,0.0)
    atr_s=pd.Series(tr).rolling(period).mean()
    pdi=100*pd.Series(pdm).rolling(period).mean()/atr_s
    mdi=100*pd.Series(mdm).rolling(period).mean()/atr_s
    dx=100*np.abs(pdi-mdi)/(pdi+mdi).replace(0,np.nan)
    adx=dx.rolling(period).mean().fillna(20).values
    return {'atr_ratio':atr_ratio,'bb_width':bb_arr,'volume_ratio':vr_arr,'adx':adx}

def make_features(df):
    f=vec_features(df)
    ar=f['atr_ratio']; adx=f['adx']
    regime=np.full(len(ar),'TRANSITION',dtype=object)
    regime[ar<0.7]='COMPRESSION'
    regime[(ar>=0.7)&(adx>30)]='TRENDING'
    regime[(ar>=0.7)&(adx<20)]='RANGE'
    feats=[]
    for i in range(len(df)):
        oic=df['oi_change_pct'].iloc[i]
        feats.append({
            'atr_ratio':float(ar[i]) if not np.isnan(ar[i]) else 1.0,
            'bb_width':float(f['bb_width'][i]) if not np.isnan(f['bb_width'][i]) else 0,
            'volume_ratio':float(f['volume_ratio'][i]) if not np.isnan(f['volume_ratio'][i]) else 1.0,
            'adx':float(adx[i]),
            'oi_change_pct':float(oic) if not np.isnan(oic) else 0.0,
            'funding':float(df['funding_rate'].iloc[i]) if not np.isnan(df['funding_rate'].iloc[i]) else 0.0,
            'regime':regime[i],
        })
    return feats

def detect_events(df, feats, vol_threshold=1.3, breakout_watch=5):
    setup_events=[];trigger_events=[]
    current=None; exit_ct=0
    closes=df['close'].values;highs=df['high'].values;lows=df['low'].values
    timestamps=list(df.index)
    for i in range(20,len(df)):
        feat=feats[i]
        if feat is None: continue
        is_comp=feat['atr_ratio']<0.7 and feat['bb_width']<0.05
        if is_comp:
            if current is None:
                current={'episode_id':f"C{len(setup_events)+1:03d}",'start_bar':i}
                setup_events.append({'episode_id':current['episode_id'],'bar_idx':i,**feat})
            exit_ct=0
        else:
            if current is not None:
                ep_high=highs[current['start_bar']:i].max()
                ep_low=lows[current['start_bar']:i].min()
                direction=None
                if closes[i]>ep_high*1.001 and feat['volume_ratio']>vol_threshold: direction='LONG'
                elif closes[i]<ep_low*0.999 and feat['volume_ratio']>vol_threshold: direction='SHORT'
                if direction:
                    trig_feat=dict(feat)
                    if i-1>=0:
                        prev=feats[i-1]
                        trig_feat['regime']=prev['regime'] if prev else feat['regime']
                        trig_feat['adx_before']=prev['adx'] if prev else feat['adx']
                        trig_feat['oi_before']=prev['oi_change_pct'] if prev else feat['oi_change_pct']
                    trigger_events.append({'episode_id':current['episode_id'],'bar_idx':i,
                        'direction':direction,'timestamp':str(timestamps[i]),**trig_feat})
                    current=None;exit_ct=0
                else:
                    exit_ct+=1
                    if exit_ct>breakout_watch: current=None;exit_ct=0
    return setup_events,trigger_events

def compute_forward(df,triggers,horizons=[1,3,6,12,24]):
    closes=df['close'].values;outs=[]
    for ev in triggers:
        i=ev['bar_idx'];entry=closes[i];d=ev['direction']
        o=dict(ev);o['event_id']=f"{ev['episode_id']}_{i}"
        for h in horizons:
            j=min(i+h,len(closes)-1);r=(closes[j]/entry-1)*100
            if d=='SHORT':r=-r
            o[f'forward_{h}bar']=round(r,4)
        # MFE/MAE
        for h in [1,3,6,12,24]:
            end=min(i+h,len(closes)-1);mfe=mae=0
            for k in range(i,end+1):
                r=(closes[k]/entry-1)*100
                if d=='SHORT':r=-r
                mfe=max(mfe,r);mae=min(mae,r)
            o[f'mfe_{h}bar']=round(mfe,4);o[f'mae_{h}bar']=round(mae,4)
        outs.append(o)
    return outs

def stats(events):
    if not events: return None
    r1=[e.get('forward_1bar',0) for e in events]
    wins=[x for x in r1 if x>0];losses=[x for x in r1 if x<=0]
    fee=0.0008
    gross=sum(r1)/len(r1);net=gross-fee*100
    npf=(sum(wins)-fee*100*len(wins))/(-sum(losses)+fee*100*len(losses)) if losses else float('inf')
    sd=statistics.stdev(r1) if len(r1)>1 else 0
    tstat=(sum(r1)/len(r1))/(sd/math.sqrt(len(r1))) if sd>0 else 0
    # p-value two-tailed from t-distribution approx (n>30 normal approx)
    pval=None
    if tstat!=0 and len(r1)>1:
        # normal approx: p = 2*(1-Phi(|t|))
        pval=2*(1-0.5*(1+math.erf(abs(tstat)/math.sqrt(2))))
    return {'n':len(events),'gross_exp':round(gross,4),'net_exp':round(net,4),
            'net_pf':round(npf,3),'tstat':round(tstat,3),'pval_raw':round(pval,4) if pval else None,
            'hit':round(sum(1 for x in r1 if x>0)/len(r1)*100,1),
            'long':sum(1 for e in events if e['direction']=='LONG'),
            'short':sum(1 for e in events if e['direction']=='SHORT'),'t0':str(events[0].get('timestamp','')),'t1':str(events[-1].get('timestamp',''))}

def holm_bonferroni(pvals):
    """Holm-Bonferroni adjustment; returns dict of adjusted p per original index."""
    n=len(pvals)
    order=sorted(range(n), key=lambda i: pvals[i])
    adj={}
    for rank,idx in enumerate(order):
        m=n-rank
        adj[idx]=min(1.0, pvals[idx]*m)
    # enforce monotonicity
    prev=0
    for rank in reversed(range(n)):
        idx=order[rank]
        adj[idx]=max(adj[idx],prev)
        prev=adj[idx]
    return [adj[i] for i in range(n)]

def bh_fdr(pvals):
    """Benjamini-Hochberg FDR."""
    n=len(pvals)
    order=sorted(range(n), key=lambda i: pvals[i])
    adj={}
    for rank,idx in enumerate(order):
        adj[idx]=min(1.0, pvals[idx]*n/(rank+1))
    # enforce monotonicity from largest
    prev=1.0
    for rank in reversed(range(n)):
        idx=order[rank]
        adj[idx]=min(adj[idx],prev)
        prev=adj[idx]
    return [adj[i] for i in range(n)]

print("="*70)
print("P1.7 ANTI-DATA-SNOOPING: temporal split + MTC + ADX curve")
print("="*70)

symbols=['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','XRPUSDT']
all_df={};all_triggers=[]
timestamps={}

for symbol in symbols:
    df=load_symbol(symbol)
    if df is None: continue
    all_df[symbol]=df
    feats=make_features(df)
    _,trig=detect_events(df,feats)
    outs=compute_forward(df,trig)
    for o in outs: o['symbol']=symbol
    # Attach real timestamp (datetime) for temporal split
    for o in outs:
        o['ts']=pd.to_datetime(o['timestamp'])
    all_triggers.extend(outs)
    print(f"  {symbol}: {len(outs)} triggers")

print(f"\nTOTAL: {len(all_triggers)} triggers")

# ================================================================
# STEP 1: PER-SYMBOL TEMPORAL SPLIT (proper)
# TRAIN: <2025-07-01, VAL: 2025-07-01..2026-01-01, TEST: >=2026-01-01
# ================================================================
train_cut=pd.Timestamp('2025-07-01',tz='UTC')
val_cut=pd.Timestamp('2026-01-01',tz='UTC')

def assign_split(o):
    ts=o['ts']
    if ts < train_cut: return 'TRAIN'
    elif ts < val_cut: return 'VAL'
    else: return 'TEST'

for o in all_triggers:
    o['split']=assign_split(o)

print("\n"+"="*70)
print("STEP 1: PER-SYMBOL TEMPORAL SPLIT")
print("="*70)
for split in ['TRAIN','VAL','TEST']:
    grp=[o for o in all_triggers if o['split']==split]
    s=stats(grp)
    if s:
        print(f"  {split}: n={s['n']}, gross={s['gross_exp']:+.3f}%, net={s['net_exp']:+.3f}%, "
              f"PF={s['net_pf']}, tstat={s['tstat']}, period={s['t0'][:10]}..{s['t1'][:10]}")

# ================================================================
# STEP 2: MULTIPLE TESTING CORRECTION for ADX buckets
# ================================================================
print("\n"+"="*70)
print("STEP 2: MULTIPLE TESTING CORRECTION (ADX buckets)")
print("="*70)
buckets=[(15,20),(20,25),(25,30),(30,35),(35,40),(40,45),(45,60)]
bucket_pvals=[]
bucket_names=[]
for lo,hi in buckets:
    grp=[e for e in all_triggers if lo<=e.get('adx_before',0)<hi]
    s=stats(grp)
    if s and s['pval_raw'] is not None:
        bucket_names.append(f"{lo}-{hi}")
        bucket_pvals.append(s['pval_raw'])

n_tests=len(bucket_pvals)
bonf=[min(1,p*n_tests) for p in bucket_pvals]
holm=holm_bonferroni(bucket_pvals)
fdr=bh_fdr(bucket_pvals)

print(f"  Total ADX buckets tested: {n_tests}")
print(f"  {'bucket':<10}{'p_raw':>9}{'p_bonf':>9}{'p_holm':>9}{'p_fdr':>9}")
print("  "+"-"*48)
for i in range(n_tests):
    sig = ' *' if fdr[i]<0.05 else ''
    print(f"  {bucket_names[i]:<10}{bucket_pvals[i]:>9.4f}{bonf[i]:>9.4f}{holm[i]:>9.4f}{fdr[i]:>9.4f}{sig}")
sig_hits=[i for i in range(n_tests) if fdr[i]<0.05]
print(f"\n  Significant after FDR (q<0.05): {[bucket_names[i] for i in sig_hits]}")
print(f"  NOTE: {'YES - survives multiple testing' if sig_hits else 'NO bucket survives FDR correction'}")

# ================================================================
# STEP 3: ADX CONTINUOUS CURVE (percentiles, not buckets)
# ================================================================
print("\n"+"="*70)
print("STEP 3: ADX CONTINUOUS CURVE (percentile bins)")
print("="*70)
adx_vals=[e.get('adx_before',0) for e in all_triggers]
pcts=np.percentile(adx_vals,[10,20,30,40,50,60,70,80,90,100])
edges=[0]+list(pcts)+[999]
print(f"  ADX percentile edges: {[round(x,1) for x in edges]}")
print(f"  {'pctile':<12}{'n':>6}{'exp1b':>9}{'net_exp':>9}{'net_PF':>8}{'tstat':>8}")
print("  "+"-"*52)
curve=[]
prev=0
for i,p in enumerate(pcts):
    grp=[e for e in all_triggers if prev<=e.get('adx_before',0)<p]
    s=stats(grp)
    if s:
        curve.append((prev,p,s['gross_exp'],s['net_exp'],s['net_pf'],s['tstat'],s['n']))
        print(f"  {prev:.0f}-{p:.0f}      {s['n']:>6}{s['gross_exp']:>+9.3f}{s['net_exp']:>+9.3f}"
              f"{s['net_pf']:>8.2f}{s['tstat']:>8.2f}")
    prev=p

# Identify local peak
if len(curve)>=3:
    max_i=max(range(len(curve)), key=lambda j: curve[j][3])  # by net_exp
    print(f"\n  Local peak net_exp at ADX {curve[max_i][0]:.0f}-{curve[max_i][1]:.0f}: "
          f"{curve[max_i][3]:+.3f}% (PF={curve[max_i][4]:.2f})")

# ================================================================
# STEP 4: FROZEN HYPOTHESIS - OOS validation of ADX sweet spot
# Use TRAIN window to FREEZE the bucket, then test on VAL/TEST (never touched)
# ================================================================
print("\n"+"="*70)
print("STEP 4: FROZEN ADX BUCKET - DISCOVERY (train) vs OOS (val+test)")
print("="*70)
train_events=[o for o in all_triggers if o['split']=='TRAIN']
val_events=[o for o in all_triggers if o['split']=='VAL']
test_events=[o for o in all_triggers if o['split']=='TEST']

# Discover best bucket ON TRAIN ONLY
print("  --- DISCOVERY ON TRAIN ONLY (freeze) ---")
train_bucket_scores=[]
for lo,hi in buckets:
    grp=[e for e in train_events if lo<=e.get('adx_before',0)<hi]
    s=stats(grp)
    if s and s['n']>=10:
        train_bucket_scores.append((lo,hi,s['net_pf'],s['net_exp'],s['n']))
        print(f"    ADX {lo}-{hi}: n={s['n']}, net_PF={s['net_pf']}, net_exp={s['net_exp']:+.3f}%")

# Freeze best on train by net_PF (require min sample)
valid=[t for t in train_bucket_scores if t[2]>1.2]
if valid:
    best=sorted(valid,key=lambda t:t[2],reverse=True)[0]
    frozen_lo,frozen_hi=best[0],best[1]
    print(f"\n  FROZEN bucket (best on TRAIN, PF>{best[2]:.2f}): ADX {frozen_lo}-{frozen_hi}")
    
    # Apply to OOS (VAL+TEST combined = the '2026 unseen' window)
    oos_events=val_events+test_events
    oos_grp=[e for e in oos_events if frozen_lo<=e.get('adx_before',0)<frozen_hi]
    s_oos=stats(oos_grp)
    if s_oos:
        print(f"\n  --- OOS VALIDATION (window 2026, never used for discovery) ---")
        print(f"    ADX {frozen_lo}-{frozen_hi} OOS: n={s_oos['n']}, gross={s_oos['gross_exp']:+.3f}%, "
              f"net={s_oos['net_exp']:+.3f}%, PF={s_oos['net_pf']}, tstat={s_oos['tstat']}, p={s_oos['pval_raw']}")
        print(f"    Period: {s_oos['t0'][:10]}..{s_oos['t1'][:10]}")
        survives = s_oos['net_pf']>1.2 and s_oos['net_exp']>0 and s_oos['n']>=10
        print(f"\n    ✓ HOLDS OOS (PF>1.2, net>0, n>=10): {'YES - Skenario B' if survives else 'NO - Skenario A (likely overfit artifact)'}")
    else:
        print(f"\n    No events in OOS window for ADX {frozen_lo}-{frozen_hi} -> cannot validate")
else:
    print(f"\n  No train bucket with net_PF>1.2 and n>=10 -> weak baseline, cautious")
    frozen_lo,frozen_hi=None,None

# Save
result={
    'analysis':'P1.7 Anti-Data-Snooping',
    'temporal_split':{'train_cut':str(train_cut),'val_cut':str(val_cut)},
    'bucket_mtc':{'buckets':bucket_names,'p_raw':bucket_pvals,
                  'p_bonferroni':bonf,'p_holm':holm,'p_fdr':fdr,'n_tests':n_tests},
    'adx_curve':[{'lo':c[0],'hi':c[1],'gross':c[2],'net':c[3],'pf':c[4],'tstat':c[5],'n':c[6]} for c in curve],
    'frozen_hypothesis':{'bucket':[frozen_lo,frozen_hi] if frozen_lo else None,
                         'discovery_on_train_only':True},
}
with open(os.path.join(RESEARCH_DIR,'anti_data_snooping.json'),'w') as f:
    json.dump(result,f,indent=2)
print("\nSaved to research/anti_data_snooping.json")
print("="*70)
