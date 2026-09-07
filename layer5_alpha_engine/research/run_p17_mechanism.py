#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-001-MECHANISM - Post-Mortem Mekanisme (NON-ALPHA / EXPLORATORY)
=====================================================================
Parent Study: STUDY-001
Status: EXPLORATORY / NON-ALPHA
Entry Definition: FROZEN (dari STUDY-001 - tidak dioptimasi)

GUARDRAIL:
  MECHANISM STUDY ≠ STRATEGY OPTIMIZATION
  DILARANG: "TP terbaik", "exit terbaik", "ADX terbaik"
  Hasil hanya OBSERVASI MEKANISTIK.

Analisis (39 simbol, entry FROZEN):
1. Time-to-Peak (time to MFE & time to MAE, distribution)
2. Return Decay Curve E[R|t] (LONG/SHORT/pooled)
3. MFE/MAE Asymmetry (rasio + distribusi, bukan hanya mean)
4. Time-to-Reversal (kapan favorable menjadi adverse)
5. Excursion Conditional Analysis (MFE 3 bar >0 vs <=0, lihat persistence)

CATATAN: Hasil TIDAK membuktikan alpha. MFE/MAE besar bisa jadi
volatility expansion biasa. Ini hanya observasi mekanistik.
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

# Entry definition FROZEN dari STUDY-001 (TIDAK dioptimasi)
PRE_REG={'adx_min':35.0,'oi_min':0.0,'compression_atr':0.7,'compression_bb':0.05,
         'vol_surge':1.3,'breakout_confirm':1.001}

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
            'adx':float(adx[i]),'oi_change_pct':float(oic) if not np.isnan(oic) else 0.0})
    return feats

def detect_events(df, feats, breakout_watch=5):
    trigger_events=[];current=None;exit_ct=0
    closes=df['close'].values;highs=df['high'].values;lows=df['low'].values
    for i in range(20,len(df)):
        feat=feats[i]
        if feat is None: continue
        is_comp=feat['atr_ratio']<PRE_REG['compression_atr'] and feat['bb_width']<PRE_REG['compression_bb']
        if is_comp:
            if current is None:
                current={'episode_id':f"E{len(trigger_events)+1:03d}",'start_bar':i}
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
                        trigger_events.append({'bar_idx':i,'direction':direction})
                    current=None;exit_ct=0
                else:
                    exit_ct+=1
                    if exit_ct>breakout_watch: current=None;exit_ct=0
    return trigger_events

# Build per-event excursion profile (0..24 bar) - the core mechanism data
def build_excursions(df, triggers, horizon=24):
    closes=df['close'].values
    events=[]
    for ev in triggers:
        i=ev['bar_idx'];entry=closes[i];d=ev['direction']
        path=[]
        for k in range(i, min(i+horizon+1, len(closes))):
            r=(closes[k]/entry-1)*100
            if d=='SHORT': r=-r
            path.append(r)
        # pad to horizon if short data
        while len(path)<=horizon: path.append(path[-1] if path else 0)
        events.append({'direction':d,'path':path})
    return events

# === MAIN ===
print("="*70)
print("STUDY-001-MECHANISM - Post-Mortem Mekanisme (EXPLORATORY/NON-ALPHA)")
print("Parent: STUDY-001 | Entry FROZEN | No optimization")
print("="*70)

all_symbols=sorted(os.listdir(DATA_DIR))
all_events=[]  # dicts with direction + path

for symbol in all_symbols:
    df=load_symbol(symbol)
    if df is None: continue
    feats=make_features(df)
    trig=detect_events(df,feats)
    evs=build_excursions(df,trig)
    for e in evs: e['symbol']=symbol
    all_events.extend(evs)

print(f"Total events (39 sym, entry FROZEN): {len(all_events)}")
longs=[e for e in all_events if e['direction']=='LONG']
shorts=[e for e in all_events if e['direction']=='SHORT']
print(f"LONG: {len(longs)}, SHORT: {len(shorts)}")

H=24

# ================================================================
# 1. TIME-TO-PEAK (time to MFE & time to MAE)
# ================================================================
print("\n"+"="*70)
print("1. TIME-TO-PEAK (bar saat MFE/MAE maksimum tercapai)")
print("="*70)

def time_to_extrema(events):
    t_mfe=[];t_mae=[]
    for e in events:
        p=e['path']
        t_mfe.append(p.index(max(p)))
        t_mae.append(p.index(min(p)))
    return t_mfe,t_mae

t_mfe, t_mae = time_to_extrema(all_events)
def pct_stats(vals):
    v=sorted(vals)
    return {'P25':v[int(len(v)*0.25)],'P50':v[int(len(v)*0.5)],
            'P75':v[int(len(v)*0.75)],'mean':round(sum(v)/len(v),2)}
print(f"  Time-to-MFE: {pct_stats(t_mfe)}")
print(f"  Time-to-MAE: {pct_stats(t_mae)}")

# % event mencapai MFE max pada 1-3 bar
early_mfe=sum(1 for t in t_mfe if t<=3)/len(t_mfe)*100
early_mae=sum(1 for t in t_mae if t<=3)/len(t_mae)*100
print(f"  % MFE maksimum tercapai dalam 1-3 bar: {early_mfe:.1f}%")
print(f"  % MAE maksimum tercapai dalam 1-3 bar: {early_mae:.1f}%")

# ================================================================
# 2. RETURN DECAY CURVE E[R|t] - LONG/SHORT/pooled
# ================================================================
print("\n"+"="*70)
print("2. RETURN DECAY CURVE E[R|t] (natural shape, bukan cari TP)")
print("="*70)
tpoints=[1,2,3,4,6,8,12,18,24]
print(f"  {'t':>4} | {'pooled':>8} {'LONG':>8} {'SHORT':>8}")
print("  "+"-"*38)
for t in tpoints:
    pooled=[e['path'][t] for e in all_events]
    l=[e['path'][t] for e in longs]
    s=[e['path'][t] for e in shorts]
    print(f"  {t:>4} | {sum(pooled)/len(pooled):>+8.3f} {sum(l)/len(l):>+8.3f} {sum(s)/len(s):>+8.3f}")

# ================================================================
# 3. MFE/MAE ASYMMETRY (rasio + distribusi)
# ================================================================
print("\n"+"="*70)
print("3. MFE/MAE ASYMMETRY - rasio MFE/|MAE| per horizon (distribusi)")
print("="*70)
def ratio_dist(events,t):
    ratios=[]
    for e in events:
        path=e['path'][:t+1]
        mfe=max(path);mae=min(path)
        denom=abs(mae)
        ratios.append(mfe/denom if denom>0 else None)
    ratios=[r for r in ratios if r is not None]
    ratios.sort()
    return {'P25':round(ratios[int(len(ratios)*0.25)],3),
            'P50':round(ratios[int(len(ratios)*0.5)],3),
            'P75':round(ratios[int(len(ratios)*0.75)],3),
            'P90':round(ratios[int(len(ratios)*0.9)],3),
            'median_mfe':round(statistics.median([max(e['path'][:t+1]) for e in events]),3),
            'median_mae':round(statistics.median([min(e['path'][:t+1]) for e in events]),3)}
for t in [1,3,6,12,24]:
    rd=ratio_dist(all_events,t)
    print(f"  t={t}: ratio median={rd['P50']}, P25={rd['P25']}, P75={rd['P75']}, P90={rd['P90']}")
    print(f"        median MFE={rd['median_mfe']}, median MAE={rd['median_mae']}")

# ================================================================
# 4. TIME-TO-REVERSAL (kapan favorable jadi adverse)
# ================================================================
print("\n"+"="*70)
print("4. TIME-TO-REVERSAL (kapan peak -> reversal)")
print("="*70)
# Untuk event yang punya MFE>0: cari bar pertama setelah peak yang turun >50% dari peak
reversal_bars=[]
for e in all_events:
    p=e['path'];peak=max(p);pk_idx=p.index(peak)
    if peak>0 and pk_idx<len(p)-1:
        # cari bar pertama setelah peak yang turun dari peak
        reversed_at=None
        for k in range(pk_idx+1,len(p)):
            if p[k] < peak*0.5:  # turun >50% dari peak
                reversed_at=k;break
        if reversed_at is not None:
            reversal_bars.append(reversed_at-pk_idx)
if reversal_bars:
    rb=sorted(reversal_bars)
    print(f"  Distribution time-to-reversal (bar setelah peak):")
    print(f"    median={rb[len(rb)//2]}, P25={rb[int(len(rb)*0.25)]}, P75={rb[int(len(rb)*0.75)]}")
    print(f"    % reversal dalam 1-3 bar: {sum(1 for r in rb if r<=3)/len(rb)*100:.1f}%")
else:
    print("  Tidak ada event yang reversal")

# ================================================================
# 5. EXCURSION CONDITIONAL ANALYSIS (persistence, bukan optimasi)
# ================================================================
print("\n"+"="*70)
print("5. EXCURSION CONDITIONAL - MFE 3bar >0 vs <=0 (persistence?)")
print("="*70)
mfe_pos=[e for e in all_events if max(e['path'][:4])>0]  # MFE in first 3 bars >0
mfe_neg=[e for e in all_events if max(e['path'][:4])<=0]
print(f"  MFE(3bar)>0: n={len(mfe_pos)} ({len(mfe_pos)/len(all_events)*100:.1f}%)")
print(f"  MFE(3bar)<=0: n={len(mfe_neg)} ({len(mfe_neg)/len(all_events)*100:.1f}%)")
# Apa yang terjadi LALU? R di 6/12/24 bar conditional
print(f"  {'t':>4} | {'MFE3>0 exp':>12} {'MFE3<=0 exp':>12}")
print("  "+"-"*32)
for t in [6,12,24]:
    r_pos=[e['path'][t] for e in mfe_pos]
    r_neg=[e['path'][t] for e in mfe_neg]
    print(f"  {t:>4} | {sum(r_pos)/len(r_pos):>+12.3f} {sum(r_neg)/len(r_neg):>+12.3f}")

# ================================================================
# Kesimpulan (observasi mekanistik, NON-ALPHA)
# ================================================================
print("\n"+"="*70)
print("KESIMPULAN (observasi mekanistik - bukan bukti alpha)")
print("="*70)
print("  Ini membandingkan dua kemungkinan:")
print("  (a) exit model breakouts salah -> asymmetry tidak dieksploitasi")
print("  (b) tidak ada exploitable asymmetry sama sekali (HANYA volatility expansion)")
print("  Data MFE/MAE simetris & membesar sampai 24 bar mendukung (b) sebagian,")
print("  namun time-to-peak & time-to-reversal memberikan informasi tambahan.")
print("  TIDAK ADA kesimpulan deployable dari studi ini.")

# Save
result={
    'study':'STUDY-001-MECHANISM',
    'status':'EXPLORATORY/NON-ALPHA',
    'parent':'STUDY-001',
    'entry_frozen':True,
    'n_events':len(all_events),
    'time_to_peak':{'mfe':pct_stats(t_mfe),'mae':pct_stats(t_mae),
                    'pct_mfe_peak_1to3':round(early_mfe,1),'pct_mae_peak_1to3':round(early_mae,1)},
    'decay_curve':{str(t):{'pooled':round(sum([e['path'][t] for e in all_events])/len(all_events),4),
        'long':round(sum([e['path'][t] for e in longs])/len(longs),4) if longs else None,
        'short':round(sum([e['path'][t] for e in shorts])/len(shorts),4) if shorts else None} for t in tpoints},
    'mfe_mae_asymmetry':{str(t):ratio_dist(all_events,t) for t in [1,3,6,12,24]},
    'time_to_reversal':{'dist':{'median':rb[len(rb)//2] if rb else None,
        'p25':sorted(rb)[int(len(rb)*0.25)] if rb else None,
        'p75':sorted(rb)[int(len(rb)*0.75)] if rb else None},
        'pct_reversal_1to3':round(sum(1 for r in rb if r<=3)/len(rb)*100,1) if rb else None},
    'conditional_excursion':{'mfe3_pos_n':len(mfe_pos),'mfe3_neg_n':len(mfe_neg),
        'fwd_6_pos':round(sum([e['path'][6] for e in mfe_pos])/len(mfe_pos),4) if mfe_pos else None,
        'fwd_6_neg':round(sum([e['path'][6] for e in mfe_neg])/len(mfe_neg),4) if mfe_neg else None},
    'guardrail':'NON-ALPHA - observasi mekanistik, tanpa strategi/deployment'
}
with open(os.path.join(RESEARCH_DIR,'STUDY-001_mechanism.json'),'w') as f:
    json.dump(result,f,indent=2)
print("\nSaved to research/STUDY-001_mechanism.json")
print("="*70)
