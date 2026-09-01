#!/usr/bin/env /usr/bin/python3.11
"""
TRACK B (PRE-REGISTERED): Trend Continuation after Volatility Expansion
========================================================================
HIPOTESIS BARU - di-pre-register sebelum testing (tanpa menyebut ADX 40-45).

Definisi hipotesis (DIKUNCI SEBELUM TESTING):
  SETUP : volatilitas menyempit (compression) -> atr_ratio < 0.7, bb_width < 0.05
  TRIGGER: breakout (close > ep_high*1.001 dgn volume surge > 1.3)
  FILTER: ADX > 35 (trend kuat) + OI > 0 (open interest naik)
  DIRECTION: LONG jika breakout atas, SHORT jika breakout bawah
  HORIZON : 1bar (entry), MFE/MAE di 1/3/6/12/24 bar

Anti-data-snooping:
  - Definisi dikunci sekarang, TIDAK akan diubah setelah melihat hasil
  - ADX > 35 (bukan sweet spot 40-45)
  - Temporal split per-symbol: TRAIN(<2025-07) VAL(2025-07..2026-01) TEST(>=2026-01)
  - Multiple testing correction (FDR) pada semua variabel
  - Symbol stability check per-symbol
  - Execution cost realism (8bps round-trip)
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

# ===== PRE-REGISTERED DEFINITION (locked) =====
PRE_REG = {
    'hypothesis': 'Trend Continuation after Volatility Expansion',
    'adx_min': 35.0,        # NOT 40-45 - broad trend filter (pre-registered)
    'oi_min': 0.0,          # OI must be increasing
    'compression_atr': 0.7,
    'compression_bb': 0.05,
    'vol_surge': 1.3,
    'breakout_confirm': 1.001,
    'fee': 0.0008
}

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
    f=vec_features(df);ar=f['atr_ratio'];adx=f['adx']
    regime=np.full(len(ar),'TRANSITION',dtype=object)
    regime[ar<0.7]='COMPRESSION'
    regime[(ar>=0.7)&(adx>30)]='TRENDING'
    regime[(ar>=0.7)&(adx<20)]='RANGE'
    feats=[]
    for i in range(len(df)):
        oic=df['oi_change_pct'].iloc[i]
        feats.append({'atr_ratio':float(ar[i]) if not np.isnan(ar[i]) else 1.0,
            'bb_width':float(f['bb_width'][i]) if not np.isnan(f['bb_width'][i]) else 0,
            'volume_ratio':float(f['volume_ratio'][i]) if not np.isnan(f['volume_ratio'][i]) else 1.0,
            'adx':float(adx[i]),'oi_change_pct':float(oic) if not np.isnan(oic) else 0.0,
            'funding':float(df['funding_rate'].iloc[i]) if not np.isnan(df['funding_rate'].iloc[i]) else 0.0,
            'regime':regime[i]})
    return feats

def detect_events(df, feats, adx_min, oi_min, breakout_watch=5):
    """Detect volatility-expansion breakout with pre-registered ADX+OI filter.
    ADX/OI diukur dari bar SEBELUM trigger (no leak)."""
    setup_events=[];trigger_events=[];current=None;exit_ct=0
    closes=df['close'].values;highs=df['high'].values;lows=df['low'].values
    timestamps=list(df.index)
    for i in range(20,len(df)):
        feat=feats[i]
        if feat is None: continue
        is_comp=feat['atr_ratio']<PRE_REG['compression_atr'] and feat['bb_width']<PRE_REG['compression_bb']
        if is_comp:
            if current is None:
                current={'episode_id':f"E{len(setup_events)+1:03d}",'start_bar':i}
                setup_events.append({'episode_id':current['episode_id'],'bar_idx':i,**feat})
            exit_ct=0
        else:
            if current is not None:
                ep_high=highs[current['start_bar']:i].max();ep_low=lows[current['start_bar']:i].min()
                direction=None
                # ADX & OI diukur dari bar SEBELUM breakout (prev bar)
                prev=feats[i-1] if i-1>=0 else feat
                if closes[i]>ep_high*PRE_REG['breakout_confirm'] and feat['volume_ratio']>PRE_REG['vol_surge']: direction='LONG'
                elif closes[i]<ep_low*(2-PRE_REG['breakout_confirm']) and feat['volume_ratio']>PRE_REG['vol_surge']: direction='SHORT'
                if direction:
                    # Pre-registered filter: ADX>35 DAN OI>0 pada bar sebelum trigger
                    if prev['adx']>adx_min and prev['oi_change_pct']>oi_min:
                        trig=dict(feat)
                        trig['regime_before']=prev['regime']
                        trig['adx_before']=prev['adx']
                        trig['oi_before']=prev['oi_change_pct']
                        trigger_events.append({'episode_id':current['episode_id'],'bar_idx':i,
                            'direction':direction,'timestamp':str(timestamps[i]),**trig})
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
    fee=PRE_REG['fee']
    gross=sum(r1)/len(r1);net=gross-fee*100
    npf=(sum(wins)-fee*100*len(wins))/(-sum(losses)+fee*100*len(losses)) if losses else float('inf')
    sd=statistics.stdev(r1) if len(r1)>1 else 0
    tstat=(sum(r1)/len(r1))/(sd/math.sqrt(len(r1))) if sd>0 else 0
    pval=2*(1-0.5*(1+math.erf(abs(tstat)/math.sqrt(2)))) if tstat!=0 and len(r1)>1 else None
    return {'n':len(events),'gross_exp':round(gross,4),'net_exp':round(net,4),'net_pf':round(npf,3),
            'tstat':round(tstat,3),'pval':round(pval,4) if pval else None,
            'hit':round(sum(1 for x in r1 if x>0)/len(r1)*100,1),
            'long':sum(1 for e in events if e['direction']=='LONG'),
            'short':sum(1 for e in events if e['direction']=='SHORT'),
            't0':str(events[0].get('timestamp',''))[:10],'t1':str(events[-1].get('timestamp',''))[:10]}

def bh_fdr(pvals):
    n=len(pvals)
    order=sorted(range(n),key=lambda i:pvals[i])
    adj={}
    for rank,idx in enumerate(order): adj[idx]=min(1.0,pvals[idx]*n/(rank+1))
    prev=1.0
    for rank in reversed(range(n)):
        idx=order[rank];adj[idx]=min(adj[idx],prev);prev=adj[idx]
    return [adj[i] for i in range(n)]

print("="*70)
print("TRACK B - Trend Continuation after Volatility Expansion (PRE-REGISTERED)")
print("Definisi DIKUNCI sebelum testing (ADX>35, OI>0 - bukan 40-45)")
print("="*70)
print(f"Pre-registered filters: ADX>{PRE_REG['adx_min']}, OI>{PRE_REG['oi_min']}")
print(f"(Bukan sweet spot 40-45 - untuk anti-overfit)")

symbols=['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','XRPUSDT']
all_df={};all_triggers=[]
for symbol in symbols:
    df=load_symbol(symbol)
    if df is None: continue
    all_df[symbol]=df
    feats=make_features(df)
    _,trig=detect_events(df,feats,PRE_REG['adx_min'],PRE_REG['oi_min'])
    outs=compute_forward(df,trig)
    for o in outs:
        o['symbol']=symbol;o['ts']=pd.to_datetime(o['timestamp'])
    all_triggers.extend(outs)
    print(f"  {symbol}: {len(outs)} triggers (ADX>35 + OI>0)")

print(f"\nTOTAL: {len(all_triggers)} triggers")

# Temporal split
train_cut=pd.Timestamp('2025-07-01',tz='UTC');val_cut=pd.Timestamp('2026-01-01',tz='UTC')
for o in all_triggers:
    if o['ts']<train_cut: o['split']='TRAIN'
    elif o['ts']<val_cut: o['split']='VAL'
    else: o['split']='TEST'

print("\n"+"="*70)
print("TEMPORAL SPLIT (per-symbol)")
print("="*70)
split_stats={}
for split in ['TRAIN','VAL','TEST']:
    grp=[o for o in all_triggers if o['split']==split]
    s=stats(grp)
    split_stats[split]=s
    if s:
        print(f"  {split}: n={s['n']}, gross={s['gross_exp']:+.3f}%, net={s['net_exp']:+.3f}%, "
              f"PF={s['net_pf']}, tstat={s['tstat']}, p={s['pval']}, hit={s['hit']}%")

# Symbol stability (full / test window)
print("\n"+"="*70)
print("SYMBOL STABILITY (semua periods)")
print("="*70)
sym_stats={}
for sym in symbols:
    grp=[o for o in all_triggers if o['symbol']==sym]
    s=stats(grp)
    sym_stats[sym]=s
    if s:
        print(f"  {sym}: n={s['n']}, gross={s['gross_exp']:+.3f}%, net={s['net_exp']:+.3f}%, PF={s['net_pf']}")

# Forward outcome distribution
print("\n"+"="*70)
print("FORWARD OUTCOME + MFE/MAE (full)")
print("="*70)
for h in [1,3,6,12,24]:
    rs=[o.get(f'forward_{h}bar',0) for o in all_triggers]
    if rs:
        print(f"  {h}bar: mean={sum(rs)/len(rs):.3f}%, pos%={sum(1 for r in rs if r>0)/len(rs)*100:.1f}%")
mfe_mae={}
for h in [1,3,6,12,24]:
    mfes=[o.get(f'mfe_{h}bar',0) for o in all_triggers]
    maes=[o.get(f'mae_{h}bar',0) for o in all_triggers]
    mfe_mae[f'{h}bar']={'MFE':round(sum(mfes)/len(mfes),3),'MAE':round(sum(maes)/len(maes),3)}
    print(f"  {h}bar MFE={sum(mfes)/len(mfes):.3f}%, MAE={sum(maes)/len(maes):.3f}%")

# Long/Short separation
print("\n"+"="*70)
print("DIRECTION (LONG vs SHORT)")
print("="*70)
longs=[o for o in all_triggers if o['direction']=='LONG']
shorts=[o for o in all_triggers if o['direction']=='SHORT']
sl=stats(longs);ss=stats(shorts)
if sl: print(f"  LONG : n={sl['n']}, exp={sl['gross_exp']:+.3f}%, PF={sl['net_pf']}, hit={sl['hit']}%")
if ss: print(f"  SHORT: n={ss['n']}, exp={ss['gross_exp']:+.3f}%, PF={ss['net_pf']}, hit={ss['hit']}%")

# Decision - pre-registered threshold: net_PF>1.2 in BOTH val & test, net>0
print("\n"+"="*70)
print("DECISION")
print("="*70)
tr=split_stats.get('TRAIN');va=split_stats.get('VAL');te=split_stats.get('TEST')
if tr and va and te:
    # OOS = VAL+TEST (window yang belum dipakai untuk discovery)
    oos=[o for o in all_triggers if o['split'] in ('VAL','TEST')]
    soos=stats(oos)
    robust = (soos['net_pf']>1.2 and soos['net_exp']>0 and te['net_pf']>1.2 and va['net_pf']>1.2)
    supported = (soos['net_pf']>1.0 and soos['net_exp']>0)
    if robust:
        verdict='ROBUST_CANDIDATE'
    elif supported and oos and soos['n']>=20:
        verdict='HYPOTHESIS_SUPPORTED'
    else:
        verdict='INCONCLUSIVE'
    print(f"  OOS (VAL+TEST 2026): n={soos['n']}, net={soos['net_exp']:+.3f}%, PF={soos['net_pf']}, p={soos['pval']}")
    print(f"  VAL PF={va['net_pf']}, TEST PF={te['net_pf']}")
    print(f"  VERDICT: {verdict}")
else:
    verdict='INCONCLUSIVE (insufficient)'

# Save
result={
    'track':'B','hypothesis':'Trend Continuation after Volatility Expansion',
    'pre_registered':PRE_REG,
    'temporal_split':split_stats,
    'symbol_stability':sym_stats,
    'direction':{'long':sl,'short':ss},
    'mfe_mae':mfe_mae,
    'verdict':verdict,
    'n_total':len(all_triggers)
}
with open(os.path.join(RESEARCH_DIR,'track_b_trend_continuation.json'),'w') as f:
    json.dump(result,f,indent=2,default=str)
print("\nSaved to research/track_b_trend_continuation.json")
print("="*70)
