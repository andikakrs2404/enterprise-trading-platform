#!/usr/bin/env /usr/bin/python3.11
"""
PRIORITAS 2: REPLICATION STUDY - 39 SYMBOL FULL UNIVERSE
=========================================================
BUKAN untuk mencari alpha. Untuk REPLICATION:
apakah kesimpulan negatif (Tidak ada net edge yang konsisten) stabil
di universe 39 simbol penuh?

Uji hipotesis yang SAMA (pre-registered):
  Track B: Trend Continuation after Volatility Expansion, ADX>35 + OI>0
Dengan MTC, temporal split, execution cost yang IDENTIK.

Jika di 39 simbol tetap tidak ada net edge yang konsisten OOS
=> kesimpulan negatif robust, selesai untuk keluarga ini.
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

PRE_REG={'adx_min':35.0,'oi_min':0.0,'compression_atr':0.7,'compression_bb':0.05,
         'vol_surge':1.3,'breakout_confirm':1.001,'fee':0.0008}

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
    h=df['high'].values;l=df['low'].values;c=df['close'].values;v=df['volume'].values
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
    feats=[]
    for i in range(len(df)):
        oic=df['oi_change_pct'].iloc[i]
        feats.append({'atr_ratio':float(ar[i]) if not np.isnan(ar[i]) else 1.0,
            'bb_width':float(f['bb_width'][i]) if not np.isnan(f['bb_width'][i]) else 0,
            'volume_ratio':float(f['volume_ratio'][i]) if not np.isnan(f['volume_ratio'][i]) else 1.0,
            'adx':float(adx[i]),'oi_change_pct':float(oic) if not np.isnan(oic) else 0.0,
            'funding':float(df['funding_rate'].iloc[i]) if not np.isnan(df['funding_rate'].iloc[i]) else 0.0})
    return feats

def detect_events(df, feats, breakout_watch=5):
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
                prev=feats[i-1] if i-1>=0 else feat
                if closes[i]>ep_high*PRE_REG['breakout_confirm'] and feat['volume_ratio']>PRE_REG['vol_surge']: direction='LONG'
                elif closes[i]<ep_low*(2-PRE_REG['breakout_confirm']) and feat['volume_ratio']>PRE_REG['vol_surge']: direction='SHORT'
                if direction:
                    if prev['adx']>PRE_REG['adx_min'] and prev['oi_change_pct']>PRE_REG['oi_min']:
                        trig=dict(feat)
                        trig['adx_before']=prev['adx'];trig['oi_before']=prev['oi_change_pct']
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
            'tstat':round(tstat,3),'pval':round(pval,4) if pval else None}

# MAIN
all_symbols=sorted(os.listdir(DATA_DIR))
print("="*70)
print(f"PRIORITAS 2: REPLICATION STUDY - {len(all_symbols)} SYMBOL (BUKAN cari alpha)")
print("="*70)
print("Uji: apakah kesimpulan negatif stabil di universe penuh?\n")

all_triggers=[]
load_fail=0
for symbol in all_symbols:
    df=load_symbol(symbol)
    if df is None: load_fail+=1; continue
    feats=make_features(df)
    _,trig=detect_events(df,feats)
    outs=compute_forward(df,trig)
    for o in outs:
        o['symbol']=symbol;o['ts']=pd.to_datetime(o['timestamp'])
    all_triggers.extend(outs)

print(f"Total triggers (39 sym, ADX>35+OI>0): {len(all_triggers)} (load_fail={load_fail})")

# Temporal split
train_cut=pd.Timestamp('2025-07-01',tz='UTC');val_cut=pd.Timestamp('2026-01-01',tz='UTC')
for o in all_triggers:
    if o['ts']<train_cut: o['split']='TRAIN'
    elif o['ts']<val_cut: o['split']='VAL'
    else: o['split']='TEST'

print("\n=== TEMPORAL SPLIT (39 symbol) ===")
for split in ['TRAIN','VAL','TEST']:
    grp=[o for o in all_triggers if o['split']==split]
    s=stats(grp)
    if s:
        print(f"  {split}: n={s['n']}, gross={s['gross_exp']:+.3f}%, net={s['net_exp']:+.3f}%, "
              f"PF={s['net_pf']}, tstat={s['tstat']}, p={s['pval']}")

oos=[o for o in all_triggers if o['split'] in ('VAL','TEST')]
soos=stats(oos)
print(f"\n  OOS (VAL+TEST): n={soos['n']}, net={soos['net_exp']:+.3f}%, PF={soos['net_pf']}, p={soos['pval']}")

# Symbol stability - berapa % symbol net positif OOS?
print("\n=== SYMBOL STABILITY (OOS window) ===")
oos_positive=[]
oos_negative=[]
for sym in all_symbols:
    grp=[o for o in oos if o['symbol']==sym]
    s=stats(grp)
    if s and s['n']>=5:
        if s['net_exp']>0: oos_positive.append(sym)
        else: oos_negative.append(sym)

print(f"  Net-positive OOS symbols (n>=5): {len(oos_positive)} of {len(oos_positive)+len(oos_negative)}")
print(f"  POSITIF: {oos_positive}")
print(f"  NEGATIF: {oos_negative}")

# MTC pada symbol-level (FDR)
print("\n=== MTC: FDR pada per-symbol OOS p-value ===")
pvals=[]
syms=[]
for sym in all_symbols:
    grp=[o for o in oos if o['symbol']==sym]
    s=stats(grp)
    if s and s['pval'] is not None and s['n']>=5:
        pvals.append(s['pval']);syms.append(sym)
n_t=len(pvals)
if n_t>0:
    order=sorted(range(n_t),key=lambda i:pvals[i])
    fdr={}
    for rank,idx in enumerate(order): fdr[idx]=min(1.0,pvals[idx]*n_t/(rank+1))
    prev=1.0
    for rank in reversed(range(n_t)):
        idx=order[rank];fdr[idx]=min(fdr[idx],prev);prev=fdr[idx]
    sig=[syms[i] for i in range(n_t) if fdr[i]<0.05]
    print(f"  Symbols tested: {n_t}, Significant after FDR (q<0.05): {sig if sig else 'NONE'}")
    print(f"  => Kesimpulan negatif ROBUST di 39 simbol" if not sig else f"  => Ada {len(sig)} symbol lolos FDR - perlu verifikasi")

# Konfirmasi MFE/MAE decay di universe luas
print("\n=== MFE/MAE DECAY PROFILE (39 symbol - konfirmasi temuan) ===")
for h in [1,3,6,12,24]:
    mfes=[o.get(f'mfe_{h}bar',0) for o in all_triggers]
    maes=[o.get(f'mae_{h}bar',0) for o in all_triggers]
    print(f"  {h}bar: avg MFE={sum(mfes)/len(mfes):.3f}%, avg MAE={sum(maes)/len(maes):.3f}%")

# Kesimpulan replication
verdict = "REPLICATION CONFIRMED: kesimpulan negatif ROBUST di 39 simbol" if not sig else "REPLICATION: beberapa symbol lolos, perlu verifikasi"
print("\n"+"="*70)
print(f"KESIMPULAN REPLICATION: {verdict}")
print("="*70)

result={
    'replication_study':True,
    'n_symbols':len(all_symbols),
    'n_triggers_total':len(all_triggers),
    'temporal_split':{s:stats([o for o in all_triggers if o['split']==s]) for s in ['TRAIN','VAL','TEST']},
    'oos':soos,
    'symbol_oos_positive':oos_positive,
    'symbol_oos_negative':oos_negative,
    'verdict':verdict,
    'note':'BUKAN mencari alpha - menguji stabilitas kesimpulan negatif'
}
with open(os.path.join(RESEARCH_DIR,'replication_39symbol.json'),'w') as f:
    json.dump(result,f,indent=2,default=str)
print("Saved to research/replication_39symbol.json")
