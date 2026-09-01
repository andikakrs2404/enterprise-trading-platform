#!/usr/bin/env /usr/bin/python3.11
"""
P1.7 WITH OI + ADX + REGIME - OPTIMIZED VECTORIZED VERSION
Menggunakan numpy vectorized untuk ADX + regime (cepat, bukan O(n^2)).
"""
import json, os, sys, math, random, statistics
import pyarrow.parquet as pq
import pandas as pd
import numpy as np

DATA_DIR = '/home/rtk/Bot-Multi-Edge-metrics/data/klines'
MET_DIR = '/home/rtk/Bot-Multi-Edge-metrics/data/metrics'
FUND_DIR = '/home/rtk/Bot-Multi-Edge-metrics/data/funding'
RESEARCH_DIR = '/home/rtk/enterprise-trading-platform/layer5_alpha_engine/research'
os.makedirs(RESEARCH_DIR, exist_ok=True)

random.seed(42); np.random.seed(42)

def load_symbol(symbol):
    k = os.path.join(DATA_DIR, symbol, 'klines_1h.parquet')
    m = os.path.join(MET_DIR, symbol, 'metrics_1h.parquet')
    f = os.path.join(FUND_DIR, symbol, 'funding_1h.parquet')
    if not os.path.exists(k): return None
    df = pd.read_parquet(k)[['open','high','low','close','volume']].copy()
    df.index = pd.to_datetime(df.index, utc=True)
    if os.path.exists(m):
        met = pd.read_parquet(m)
        met.index = pd.to_datetime(met.index, utc=True)
        df = df.join(met[['sum_open_interest']], how='left')
        df['oi_delta'] = df['sum_open_interest'].diff()
        df['oi_change_pct'] = df['sum_open_interest'].pct_change()*100
    else:
        df['sum_open_interest'] = np.nan; df['oi_delta']=np.nan; df['oi_change_pct']=np.nan
    if os.path.exists(f):
        fund = pd.read_parquet(f)
        fund.index = pd.to_datetime(fund.index, utc=True)
        df = df.join(fund[['funding_rate']], how='left')
    else:
        df['funding_rate'] = np.nan
    return df

# ---- Vectorized ATR, ADX, BB, volume ----
def vec_features(df, period=14):
    o=df['open'].values; h=df['high'].values; l=df['low'].values
    c=df['close'].values; v=df['volume'].values; n=len(df)
    
    # True range
    hl = h-l
    hc = np.abs(h - np.roll(c,1)); hc[0]=0
    lc = np.abs(l - np.roll(c,1)); lc[0]=0
    tr = np.maximum(hl, np.maximum(hc, lc))
    
    # ATR via rolling mean (simple)
    atr = pd.Series(tr).rolling(period).mean().values
    atr100 = pd.Series(tr).rolling(100).mean().values
    atr100 = np.where(np.isnan(atr100), atr, atr100)
    atr_ratio = np.where(atr100>0, atr/atr100, 1.0)
    
    # BB width (20)
    closes = pd.Series(c)
    sma20 = closes.rolling(20).mean()
    std20 = closes.rolling(20).std()
    bb_width_arr = np.where((sma20>0).values, (4*std20/sma20).values, 0.0)
    
    # Volume ratio (20)
    vol_sma = pd.Series(v).rolling(20).mean()
    vol_ratio_arr = np.where((vol_sma>0).values, (v/vol_sma).values, 1.0)
    
    # ADX vectorized
    up_move = h - np.roll(h,1); up_move[0]=0
    dn_move = np.roll(l,1) - l; dn_move[0]=0
    plus_dm = np.where((up_move>dn_move)&(up_move>0), up_move, 0.0)
    minus_dm = np.where((dn_move>up_move)&(dn_move>0), dn_move, 0.0)
    atr_s = pd.Series(tr).rolling(period).mean()
    plus_di = 100*pd.Series(plus_dm).rolling(period).mean()/atr_s
    minus_di = 100*pd.Series(minus_dm).rolling(period).mean()/atr_s
    dx = 100*np.abs(plus_di-minus_di)/(plus_di+minus_di).replace(0,np.nan)
    adx = dx.rolling(period).mean().fillna(20).values
    
    return {
        'atr_ratio': atr_ratio,
        'bb_width': bb_width_arr,
        'volume_ratio': vol_ratio_arr,
        'adx': adx,
    }

def classify_regime(atr_ratio_arr, adx_arr):
    regime = np.full(len(atr_ratio_arr), 'TRANSITION', dtype=object)
    regime[atr_ratio_arr < 0.7] = 'COMPRESSION'
    m = (atr_ratio_arr >= 0.7) & (adx_arr > 30)
    regime[m] = 'TRENDING'
    m2 = (atr_ratio_arr >= 0.7) & (adx_arr < 20)
    regime[m2] = 'RANGE'
    return regime

def make_features(df):
    f = vec_features(df)
    regime = classify_regime(f['atr_ratio'], f['adx'])
    feats = []
    for i in range(len(df)):
        oi_c = df['oi_change_pct'].iloc[i]
        feats.append({
            'atr_ratio': float(f['atr_ratio'][i]) if not np.isnan(f['atr_ratio'][i]) else 1.0,
            'bb_width': float(f['bb_width'][i]) if not np.isnan(f['bb_width'][i]) else 0,
            'volume_ratio': float(f['volume_ratio'][i]) if not np.isnan(f['volume_ratio'][i]) else 1.0,
            'adx': float(f['adx'][i]),
            'oi_change_pct': float(oi_c) if not np.isnan(oi_c) else 0.0,
            'funding': float(df['funding_rate'].iloc[i]) if not np.isnan(df['funding_rate'].iloc[i]) else 0.0,
            'regime': regime[i],
        })
    return feats

def detect_events(df, feats, vol_threshold=1.3, filters=None, breakout_watch=5):
    setup_events=[]; trigger_events=[]
    current=None
    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    exit_countdown = 0
    for i in range(20, len(df)):
        feat = feats[i]
        if feat is None: continue
        if filters:
            skip = False
            if 'adx_min' in filters and feat['adx'] < filters['adx_min']: skip=True
            if 'oi_min' in filters and feat['oi_change_pct'] < filters['oi_min']: skip=True
            if 'regimes' in filters and feat['regime'] not in filters['regimes']: skip=True
            if 'funding_min' in filters and feat['funding'] < filters['funding_min']: skip=True
            if skip: continue
        is_comp = feat['atr_ratio'] < 0.7 and feat['bb_width'] < 0.05
        if is_comp:
            if current is None:
                current = {'episode_id':f"C{len(setup_events)+1:03d}",'start_bar':i}
                setup_events.append({'episode_id':current['episode_id'],'bar_idx':i,**feat})
            exit_countdown = 0
        else:
            # In breakout watch window after episode ended
            if current is not None:
                # CRITICAL: range dihitung HANYA dari compression bars (exclude current bar i)
                # Mencegah forward-looking leak (ep_high tidak termasuk bar breakout sendiri)
                ep_high = highs[current['start_bar']:i].max()
                ep_low = lows[current['start_bar']:i].min()
                direction=None
                if closes[i] > ep_high*1.001 and feat['volume_ratio']>vol_threshold: direction='LONG'
                elif closes[i] < ep_low*0.999 and feat['volume_ratio']>vol_threshold: direction='SHORT'
                if direction:
                    trigger_events.append({'episode_id':current['episode_id'],'bar_idx':i,'direction':direction,**feat})
                    current=None
                    exit_countdown = 0
                else:
                    exit_countdown += 1
                    if exit_countdown > breakout_watch:
                        current = None
                        exit_countdown = 0
            else:
                exit_countdown = 0
    return setup_events, trigger_events

def compute_forward(df, triggers, horizons=[1,3,6,12,24]):
    closes=df['close'].values
    outs=[]
    for ev in triggers:
        i=ev['bar_idx']; entry=closes[i]; d=ev['direction']
        o=dict(ev); o['event_id']=f"{ev['episode_id']}_{i}"
        for h in horizons:
            j=min(i+h,len(closes)-1)
            r=(closes[j]/entry-1)*100
            if d=='SHORT': r=-r
            o[f'forward_{h}bar']=round(r,4)
        for h in horizons:
            end=min(i+h,len(closes)-1); mfe=mae=0
            for k in range(i,end+1):
                r=(closes[k]/entry-1)*100
                if d=='SHORT': r=-r
                mfe=max(mfe,r); mae=min(mae,r)
            o[f'mfe_{h}bar']=round(mfe,4); o[f'mae_{h}bar']=round(mae,4)
        outs.append(o)
    return outs

def permutation_test(cf,bf,n_iter=1000):
    nc,nb=len(cf),len(bf)
    if nc==0 or nb==0: return None
    cc=[1 if f.get('forward_1bar',0)>0 else 0 for f in cf]
    bb=[1 if f.get('forward_1bar',0)>0 else 0 for f in bf]
    obs=(sum(cc)/nc)-(sum(bb)/nb)
    pooled=cc+bb; count=0
    for _ in range(n_iter):
        random.shuffle(pooled)
        if abs((sum(pooled[:nc])/nc)-(sum(pooled[nc:])/nb))>=abs(obs): count+=1
    return count/n_iter

def effect_size(cf,bf):
    nc,nb=len(cf),len(bf)
    if nc==0 or nb==0: return None
    pc=sum(1 for f in cf if f.get('forward_1bar',0)>0)/nc
    pb=sum(1 for f in bf if f.get('forward_1bar',0)>0)/nb
    ad=(pc-pb)*100
    return {'p_compression':round(pc,4),'p_baseline':round(pb,4),
            'absolute_delta_pp':round(ad,2),
            'relative_lift_pct':round((pc-pb)/pb*100,2) if pb>0 else None,
            'odds_ratio':round((pc/(1-pc))/(pb/(1-pb)),3) if pb not in (0,1) and pc not in (0,1) else None,
            'n_compression':nc,'n_baseline':nb}

def make_decision(effect,pv,ne,nei,longs,shorts,eco):
    if effect is None or ne==0: return {'state':'INCONCLUSIVE','reason':'No events','level':0}
    ad=effect['absolute_delta_pp']; p=pv if pv is not None else 1.0
    nex=eco.get('net_expectancy',0); npf=eco.get('net_pf',0)
    if p>0.05 or ad<2.0:
        return {'state':'INCONCLUSIVE','reason':f'Not sig (p={p:.3f}) or small (delta={ad:.1f}pp)','level':1}
    if nex>0 and ad>=2.0:
        return {'state':'HYPOTHESIS_SUPPORTED','reason':f'Sig effect (delta={ad:.1f}pp,p={p:.3f})','level':2}
    if nex>0 and npf>1.2 and nei>=3:
        return {'state':'ROBUST_CANDIDATE','reason':f'Robust (delta={ad:.1f}pp,PF={npf:.2f})','level':3}
    if nex>0.05 and npf>1.5 and ne>=50:
        return {'state':'PRODUCTION_CANDIDATE','reason':f'Prod (delta={ad:.1f}pp,PF={npf:.2f})','level':4}
    return {'state':'HYPOTHESIS_SUPPORTED','reason':f'Supported (delta={ad:.1f}pp)','level':2}

print("="*70)
print("P1.7 REFINEMENT - OI + ADX + REGIME + FUNDING (VECTORIZED)")
print("="*70)

symbols=['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','XRPUSDT']
all_df={}; all_triggers=[]

for symbol in symbols:
    df=load_symbol(symbol)
    if df is None: print(f"  [!]{symbol} skip"); continue
    all_df[symbol]=df
    feats=make_features(df)
    # BASE (no filter)
    sb,tb=detect_events(df,feats)
    # FILTERED
    sf,tf=detect_events(df,feats,filters={'adx_min':25,'oi_min':-0.5,
        'regimes':['COMPRESSION','TRENDING']})
    print(f"\n--- {symbol} ---")
    print(f"  Bars:{len(df)}, Setup(base):{len(sb)}, Trigger(base):{len(tb)}")
    print(f"  Trigger(filtered ADX+OI+regime):{len(tf)}")
    outs=compute_forward(df,tf)
    for o in outs: o['symbol']=symbol
    all_triggers.extend(outs)

print("\n"+"="*70)
print(f"TOTAL FILTERED TRIGGERS: {len(all_triggers)}")
print("="*70)
longs=[t for t in all_triggers if t['direction']=='LONG']
shorts=[t for t in all_triggers if t['direction']=='SHORT']
print(f"LONG:{len(longs)}, SHORT:{len(shorts)}")

regimes={}
for t in all_triggers: regimes[t['regime']]=regimes.get(t['regime'],0)+1
print(f"Regime dist:{regimes}")

print("\n--- FORWARD OUTCOME (FILTERED) ---")
for h in [1,3,6,12,24]:
    rs=[t.get(f'forward_{h}bar',0) for t in all_triggers]
    if rs:
        pos=sum(1 for r in rs if r>0)
        print(f"  {h}bar: mean={sum(rs)/len(rs):.3f}%, pos%={pos/len(rs)*100:.1f}% (n={len(rs)})")

random.seed(123); baseline_fwd=[]
for _ in range(len(all_triggers)):
    sym=random.choice(list(all_df.keys())); d=all_df[sym]
    ri=random.randint(50,len(d)-30)
    entry=d['close'].iloc[ri]; direction=random.choice(['LONG','SHORT'])
    r=(d['close'].iloc[ri+1]/entry-1)*100
    if direction=='SHORT': r=-r
    baseline_fwd.append({'forward_1bar':r})

effect=effect_size(all_triggers,baseline_fwd)
pv=permutation_test(all_triggers,baseline_fwd)
print("\n--- EFFECT SIZE (FILTERED INCL OI/ADX/REGIME) ---")
if effect:
    print(f"  P(comp):{effect['p_compression']*100:.1f}% (n={effect['n_compression']})")
    print(f"  P(base):{effect['p_baseline']*100:.1f}% (n={effect['n_baseline']})")
    print(f"  Abs delta:{effect['absolute_delta_pp']:+.1f} pp")
    if effect['relative_lift_pct']: print(f"  Rel lift:{effect['relative_lift_pct']:+.1f}%")
    if effect['odds_ratio']: print(f"  Odds ratio:{effect['odds_ratio']:.2f}")
print(f"  Permutation p:{pv:.4f}")

fee_rate=0.0008
gross=sum(t.get('forward_1bar',0) for t in all_triggers)/len(all_triggers) if all_triggers else 0
net=gross-fee_rate*100
wins=[t['forward_1bar'] for t in all_triggers if t.get('forward_1bar',0)>0]
losses=[t['forward_1bar'] for t in all_triggers if t.get('forward_1bar',0)<=0]
npf=(sum(wins)-fee_rate*100*len(wins))/(-sum(losses)+fee_rate*100*len(losses)) if losses else 0
print(f"\n--- ECONOMIC ---")
print(f"  Gross exp:{gross:+.3f}%, Net exp:{net:+.3f}%, Net PF:{npf:.3f}")
eco={'gross_expectancy':gross,'net_expectancy':net,'net_pf':npf,'fee_rate':fee_rate}

decision=make_decision(effect,pv,len(all_triggers),
    len(set(t['episode_id'] for t in all_triggers)),len(longs),len(shorts),eco)
print(f"\n--- DECISION ---")
print(f"  State:{decision['state']}")
print(f"  Reason:{decision['reason']}")
print(f"  Level:{decision['level']}/4")

manifest={
    'research_id':'CB-P1.7-RW-OIADX-001','status':'P1_7_COMPLETE',
    'data_source':'Bot-Multi-Edge-metrics','universe':symbols,'timeframes':['1h'],
    'n_events_total':len(all_triggers),'n_long':len(longs),'n_short':len(shorts),
    'filters':{'adx':'>25','oi':'>-0.5%','regime':['COMPRESSION','TRENDING']},
    'effect_size':effect,'permutation_pvalue':pv,'regime_distribution':regimes,
    'decision':decision['state'],'decision_reason':decision['reason'],
    'economic':eco,'corrections_applied':19,'framework_version':'v2.1-OI-ADX-REGIME'}
with open(os.path.join(RESEARCH_DIR,'research_manifest.json'),'w') as f:
    json.dump(manifest,f,indent=2)
with open(os.path.join(RESEARCH_DIR,'forward_outcomes.json'),'w') as f:
    json.dump(all_triggers,f,indent=2)
print("\n"+"="*70)
print("SAVED. FINAL DECISION:",decision['state'])
print("="*70)
