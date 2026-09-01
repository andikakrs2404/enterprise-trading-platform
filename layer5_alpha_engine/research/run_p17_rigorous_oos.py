#!/usr/bin/env /usr/bin/python3.11
"""
Verifikasi ketat: ADX 40-45 OOS per-window (pisah VAL vs TEST)
Fenomena harus stabil di DUADUA window terpisah, bukan hanya saat digabung.
Jika hanya hidup di satu window -> masih artefak/regime-spesifik.
"""
import json, os, sys, math, random, statistics
import pyarrow.parquet as pq
import pandas as pd
import numpy as np

DATA_DIR='/home/rtk/Bot-Multi-Edge-metrics/data/klines'
MET_DIR='/home/rtk/Bot-Multi-Edge-metrics/data/metrics'
FUND_DIR='/home/rtk/Bot-Multi-Edge-metrics/data/funding'
RESEARCH_DIR='/home/rtk/enterprise-trading-platform/layer5_alpha_engine/research'
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

def detect_events(df, feats, vol_threshold=1.3, breakout_watch=5):
    setup_events=[];trigger_events=[];current=None;exit_ct=0
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
                ep_high=highs[current['start_bar']:i].max();ep_low=lows[current['start_bar']:i].min()
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
    pval=2*(1-0.5*(1+math.erf(abs(tstat)/math.sqrt(2)))) if tstat!=0 and len(r1)>1 else None
    return {'n':len(events),'gross_exp':round(gross,4),'net_exp':round(net,4),'net_pf':round(npf,3),
            'tstat':round(tstat,3),'pval':round(pval,4) if pval else None,
            'long':sum(1 for e in events if e['direction']=='LONG'),
            'short':sum(1 for e in events if e['direction']=='SHORT'),
            't0':str(events[0]['timestamp'][:10]),'t1':str(events[-1]['timestamp'][:10])}

print("="*70)
print("RIGOROUS OOS CHECK: ADX 40-45 per-window (VAL vs TEST terpisah)")
print("="*70)
symbols=['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','XRPUSDT']
all_triggers=[]
for symbol in symbols:
    df=load_symbol(symbol)
    if df is None: continue
    feats=make_features(df)
    _,trig=detect_events(df,feats)
    outs=compute_forward(df,trig)
    for o in outs:
        o['symbol']=symbol
        o['ts']=pd.to_datetime(o['timestamp'])
    all_triggers.extend(outs)

train_cut=pd.Timestamp('2025-07-01',tz='UTC')
val_cut=pd.Timestamp('2026-01-01',tz='UTC')
for o in all_triggers:
    if o['ts']<train_cut: o['split']='TRAIN'
    elif o['ts']<val_cut: o['split']='VAL'
    else: o['split']='TEST'

# FROZEN dari train: ADX 40-45
frozen_lo,frozen_hi=40,45

print("\nPertanyaan: apakah ADX 40-45 stabil di DUADUA window OOS terpisah?")
print("="*70)
for split in ['VAL','TEST']:
    grp=[o for o in all_triggers if o['split']==split and frozen_lo<=o.get('adx_before',0)<frozen_hi]
    s=stats(grp)
    if s:
        verdict = 'POSITIF' if (s['net_pf']>1.2 and s['net_exp']>0) else 'TIDAK'
        print(f"\n  [{split}] ADX {frozen_lo}-{frozen_hi}: n={s['n']}, gross={s['gross_exp']:+.3f}%, "
              f"net={s['net_exp']:+.3f}%, PF={s['net_pf']}, tstat={s['tstat']}, p={s['pval']}")
        print(f"    Period: {s['t0']}..{s['t1']} | Verdict: {verdict}")
    else:
        print(f"\n  [{split}] ADX {frozen_lo}-{frozen_hi}: TIDAK ADA events (n=0)")

# Per-symbol dalam window 2026 (TEST) - apakah konsisten antar symbol?
print("\n"+"="*70)
print("DETAIL PER-SYMBOL dalam TEST window (ADX 40-45): konsisten?")
print("="*70)
for sym in symbols:
    grp=[o for o in all_triggers if o['split']=='TEST' and o['symbol']==sym
         and frozen_lo<=o.get('adx_before',0)<frozen_hi]
    s=stats(grp)
    if s:
        print(f"  {sym}: n={s['n']}, gross={s['gross_exp']:+.3f}%, net={s['net_exp']:+.3f}%, PF={s['net_pf']}")
    else:
        print(f"  {sym}: n=0")

# KESIMPULAN gabungan
print("\n"+"="*70)
print("KESIMPULAN AKHIR")
print("="*70)
