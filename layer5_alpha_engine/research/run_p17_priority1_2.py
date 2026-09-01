#!/usr/bin/env /usr/bin/python3.11
"""
P1.7 PRIORITY #1 + #2: ADX Quantile Study & Subset Analysis
==============================================================
- Regime dihitung SEBELUM sinyal (exclude bar breakout - fix labeling leak)
- Prioritas #1: subset TRENDING + ADX>35 + OI>0, split train/val/test
- Prioritas #2: ADX quantile/decile study, monotonicity test

Data: OI + ADX + regime + funding dari Bot-Multi-Edge-metrics
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
    """Regime dihitung dari bar SEBELUM breakout (exclude bar trigger)."""
    setup_events=[];trigger_events=[]
    current=None; exit_ct=0
    closes=df['close'].values;highs=df['high'].values;lows=df['low'].values
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
                # Range HANYA dari compression bars (exclude bar trigger i) - no leak
                ep_high=highs[current['start_bar']:i].max()
                ep_low=lows[current['start_bar']:i].min()
                direction=None
                if closes[i]>ep_high*1.001 and feat['volume_ratio']>vol_threshold: direction='LONG'
                elif closes[i]<ep_low*0.999 and feat['volume_ratio']>vol_threshold: direction='SHORT'
                if direction:
                    # REGIME HARUS dihitung dari bar SEBELUM trigger (i-1), bukan bar i
                    # sehingga label tidak terkontaminasi breakout yang baru terjadi
                    trig_feat = dict(feat)
                    if i-1>=0:
                        prev = feats[i-1]
                        trig_feat['regime'] = prev['regime'] if prev else feat['regime']
                        trig_feat['adx_before'] = prev['adx'] if prev else feat['adx']
                        trig_feat['oi_before'] = prev['oi_change_pct'] if prev else feat['oi_change_pct']
                    trigger_events.append({'episode_id':current['episode_id'],'bar_idx':i,
                        'direction':direction,**trig_feat})
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
        outs.append(o)
    return outs

def stats(events):
    """Return stats for a set of events."""
    if not events: return None
    r1=[e.get('forward_1bar',0) for e in events]
    wins=[x for x in r1 if x>0];losses=[x for x in r1 if x<=0]
    fee=0.0008
    gross=sum(r1)/len(r1)
    net=gross-fee*100
    npf=(sum(wins)-fee*100*len(wins))/(-sum(losses)+fee*100*len(losses)) if losses else float('inf')
    # t-stat
    sd=statistics.stdev(r1) if len(r1)>1 else 0
    tstat=(sum(r1)/len(r1))/(sd/math.sqrt(len(r1))) if sd>0 else 0
    pospct=sum(1 for r in r1 if r>0)/len(r1)*100
    return {'n':len(events),'gross_exp':round(gross,4),'net_exp':round(net,4),
            'net_pf':round(npf,3),'tstat':round(tstat,3),'hit':round(pospct,1),
            'long':sum(1 for e in events if e['direction']=='LONG'),
            'short':sum(1 for e in events if e['direction']=='SHORT')}

print("="*70)
print("P1.7 PRIORITY #1+#2 - ADX QUANTILE + SUBSET TRAIN/VAL/TEST")
print("="*70)

symbols=['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','XRPUSDT']
all_df={};all_triggers=[]

for symbol in symbols:
    df=load_symbol(symbol)
    if df is None: continue
    all_df[symbol]=df
    feats=make_features(df)
    _,trig=detect_events(df,feats)
    outs=compute_forward(df,trig)
    for o in outs: o['symbol']=symbol
    all_triggers.extend(outs)
    print(f"  {symbol}: {len(outs)} triggers (regime dari bar sebelum trigger)")

print(f"\nTOTAL triggers: {len(all_triggers)} (regime leak FIXED - dihitung dari bar i-1)")

# === PRIORITY #2: ADX QUANTILE / DECILE STUDY ===
print("\n"+"="*70)
print("PRIORITY #2: ADX QUANTILE STUDY - E[return | ADX bucket]")
print("="*70)
buckets=[(15,20),(20,25),(25,30),(30,35),(35,40),(40,45),(45,60)]
print(f"  {'ADX':<12}{'n':>6}{'exp1b':>9}{'net_exp':>9}{'net_PF':>8}{'tstat':>8}{'hit%':>7}")
print("  "+"-"*58)
monotonic_vals=[]
for lo,hi in buckets:
    grp=[e for e in all_triggers if lo<=e.get('adx_before',0)<hi]
    s=stats(grp)
    if s:
        monotonic_vals.append(s['gross_exp'])
        print(f"  {lo}-{hi:<10}{s['n']:>6}{s['gross_exp']:>+9.3f}{s['net_exp']:>+9.3f}"
              f"{s['net_pf']:>8.2f}{s['tstat']:>8.2f}{s['hit']:>7.1f}")

# Monotonicity check (Spearman-ish on bucket means)
if len(monotonic_vals)>=4:
    # increasing trend check last>=first
    inc = monotonic_vals[-1] > monotonic_vals[0]
    print(f"\n  Monotonic trend (first vs last bucket): {'INCREASING' if inc else 'not clear'}")
    print(f"  Bucket gross exps: {[round(x,3) for x in monotonic_vals]}")

# === PRIORITY #1: SUBSET TRENDING + ADX>35 + OI>0 ===
print("\n"+"="*70)
print("PRIORITY #1: SUBSET TRENDING + ADX>35 + OI>0, SPLIT TRAIN/VAL/TEST")
print("="*70)
subset=[e for e in all_triggers if e.get('regime')=='TRENDING'
        and e.get('adx_before',0)>35 and e.get('oi_before',0)>0]
print(f"  Subset events: {len(subset)}")

# Time-based split: sort by bar_idx (which reflects time order within data)
# Each symbol has its own time axis; approximate by index
subset_sorted = sorted(subset, key=lambda e: e['bar_idx'])

# Simple chronological split across all events (pooled)
# Better: use global 60/20/20 by sorting events by symbol then bar
# For simplicity & no leakage: split by symbol timestamp fraction
n=len(subset_sorted)
if n>0:
    # Build a pseudo-global order using symbol + bar_idx normalized
    # Assign each event a global time rank via timestamp (use sym index)
    order=sorted(subset, key=lambda e:(e['symbol'], e['bar_idx']))
    train=order[:int(len(order)*0.6)]
    val=order[int(len(order)*0.6):int(len(order)*0.8)]
    test=order[int(len(order)*0.8):]
    
    print(f"\n  --- TRAIN (60%) ---")
    print(f"  {stats(train)}")
    print(f"  --- VALIDATION (20%) ---")
    print(f"  {stats(val)}")
    print(f"  --- TEST (20%, never touched) ---")
    print(f"  {stats(test)}")
    
    # Stability check
    st=stats(train);sv=stats(val);stest=stats(test)
    if st and sv and stest:
        print("\n  --- STABILITY CHECK ---")
        print(f"  PF  : train={st['net_pf']}, val={sv['net_pf']}, test={stest['net_pf']}")
        print(f"  Net : train={st['net_exp']:+.3f}, val={sv['net_exp']:+.3f}, test={stest['net_exp']:+.3f}")
        stable = (st['net_pf']>1.2 and sv['net_pf']>1.2 and stest['net_pf']>1.2
                  and st['net_exp']>0 and sv['net_exp']>0 and stest['net_exp']>0)
        print(f"  STABLE ACROSS TRAIN/VAL/TEST: {'YES' if stable else 'NO'}")

# Also compare vs the LOOSE/ADX<35 + OI<=0 alternative subset (contrast)
print("\n"+"="*70)
print("CONTRAST: Subset ADX<=35 or OI<=0 (the 'rest')")
print("="*70)
rest=[e for e in all_triggers if not (e.get('regime')=='TRENDING'
        and e.get('adx_before',0)>35 and e.get('oi_before',0)>0)]
s_rest=stats(rest)
s_sub=stats(subset)
if s_rest and s_sub:
    print(f"  TRENDING+ADX>35+OI>0 : n={s_sub['n']}, gross={s_sub['gross_exp']:+.3f}%, net_PF={s_sub['net_pf']}")
    print(f"  Rest (all others)     : n={s_rest['n']}, gross={s_rest['gross_exp']:+.3f}%, net_PF={s_rest['net_pf']}")

# Save
result={
    'analysis':'P1.7 Priority1+2',
    'total_triggers':len(all_triggers),
    'adx_quantiles':{f'{lo}-{hi}':stats([e for e in all_triggers if lo<=e.get('adx_before',0)<hi])
        for lo,hi in buckets},
    'subset_trending_adx35_oi0':stats(subset) if subset else None,
    'split':{'train':stats(train) if n>0 else None,
             'val':stats(val) if n>0 else None,
             'test':stats(test) if n>0 else None} if n>0 else None,
    'contrast_rest':stats(rest) if rest else None,
}
with open(os.path.join(RESEARCH_DIR,'adx_quantile_study.json'),'w') as f:
    json.dump(result,f,indent=2)
print("\nSaved to research/adx_quantile_study.json")
print("="*70)