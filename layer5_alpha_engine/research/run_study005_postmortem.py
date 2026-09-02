#!/usr/bin/env /usr/bin/python3.11
"""STUDY-005 POST-MORTEM: Mengapa fenomena berbalik di TEST?
Bukan untuk rescue. Untuk ilmu."""
import json, os, random, statistics
import pandas as pd, numpy as np
random.seed(42); np.random.seed(42)

DATA='/home/rtk/Bot-Multi-Edge-metrics/data'
KDIR=DATA+'/klines'; MDIR=DATA+'/metrics'; FDIR=DATA+'/funding'
OUT='/home/rtk/enterprise-trading-platform/layer5_alpha_engine/research'

def load(sym):
    k=os.path.join(KDIR,sym,'klines_1h.parquet')
    m=os.path.join(MDIR,sym,'metrics_1h.parquet')
    f=os.path.join(FDIR,sym,'funding_1h.parquet')
    if not os.path.exists(k): return None
    df=pd.read_parquet(k)[['open','high','low','close','volume']].copy()
    df.index=pd.to_datetime(df.index,utc=True)
    if os.path.exists(m):
        met=pd.read_parquet(m); met.index=pd.to_datetime(met.index,utc=True)
        df=df.join(met[['sum_open_interest']],how='left')
    else: df['sum_open_interest']=np.nan
    if os.path.exists(f):
        fund=pd.read_parquet(f); fund.index=pd.to_datetime(fund.index,utc=True)
        df=df.join(fund[['funding_rate']],how='left')
    else: df['funding_rate']=np.nan
    return df

TRAIN_END=pd.Timestamp('2025-06-30', tz='UTC')
VAL_END=pd.Timestamp('2025-12-31', tz='UTC')

syms=sorted(os.listdir(KDIR))
frames=[]
for sym in syms:
    df=load(sym)
    if df is None: continue
    c=df['close']
    for h in [1,3,6,12,24]: df[f'R{h}']=(c.shift(-h)/c-1)*100
    df['sym']=sym
    df['rv']=df['close'].pct_change().rolling(100).std()
    frames.append(df)

all_df=pd.concat(frames)
all_df['fund_pct']=all_df.groupby('sym')['funding_rate'].rank(pct=True)
all_df['oi_pct']=all_df.groupby('sym')['sum_open_interest'].rank(pct=True)
all_df['FUND_LOW']=all_df['fund_pct']<0.33
all_df['OI_LOW']=all_df['oi_pct']<0.33
vol_med=all_df['rv'].median()
all_df['HIGH_VOL']=all_df['rv']>vol_med
all_df['STATE']=all_df['FUND_LOW']&all_df['OI_LOW']&all_df['HIGH_VOL']
all_df['split']=np.where(all_df.index<=TRAIN_END,'TRAIN',np.where(all_df.index<=VAL_END,'VAL','TEST'))
dc=all_df.dropna(subset=['R1','R3','R6','R12','R24','fund_pct','oi_pct','rv']).copy()

print("="*70)
print("POST-MORTEM: Mengapa fenomena berbalik di TEST?")
print("="*70)

# 1. Apa yang berubah pada DISTRIBUTION?
print("\n--- 1. DISTRIBUTION SHIFT (input features) ---")
for name in ['funding_rate','oi_pct','rv','close']:
    for s in ['TRAIN','VAL','TEST']:
        vals=dc[dc['split']==s][name].dropna()
        if len(vals)==0: continue
        print(f"  {s:>5} {name:<20} mean={vals.mean():.6f} P10={vals.quantile(.10):.6f} P50={vals.median():.6f} P90={vals.quantile(.90):.6f}")

# 2. State prevalence per split
print("\n--- 2. STATE PREVALENCE ---")
for s in ['TRAIN','VAL','TEST']:
    sub=dc[dc['split']==s]
    n_state=sub['STATE'].sum()
    print(f"  {s}: total={len(sub)}, state_active={n_state} ({n_state/len(sub)*100:.1f}%)")

# 3. Volatility regime shift
print("\n--- 3. VOLATILITY REGIME ---")
for s in ['TRAIN','VAL','TEST']:
    sub=dc[dc['split']==s]
    hv=sub[sub['rv']>vol_med]
    lv=sub[sub['rv']<=vol_med]
    # Apakah R24 berubah arah di tiap vol regime?
    for regime_name,regime_sub in [('HIGH_VOL',hv),('LOW_VOL',lv)]:
        if len(regime_sub)==0: continue
        r24=regime_sub['R24'].mean()
        print(f"  {s:>5} {regime_name}: n={len(regime_sub):>8}, E[R24]={r24:+.4f}%")

# 4. Correlation structure shift
print("\n--- 4. CORRELATION STRUCTURE ---")
for s in ['TRAIN','VAL','TEST']:
    sub=dc[dc['split']==s]
    pairs=[('fund_pct','R24'),('oi_pct','R24'),('rv','R24')]
    corrs={}
    for a,b in pairs:
        valid=sub[[a,b]].dropna()
        if len(valid)>100:
            corrs[f'{a}~{b}']=round(float(valid[a].corr(valid[b])),4)
        else:
            corrs[f'{a}~{b}']=None
    print(f"  {s}: {corrs}")

# 5. State conditioning effect (R24 state - R24 all) per split
print("\n--- 5. CONDITIONING LIFT (state - unconditional, per split) ---")
for s in ['TRAIN','VAL','TEST']:
    sub=dc[dc['split']==s]
    state=sub[sub['STATE']]
    if len(state)==0: continue
    lift=state['R24'].mean()-sub['R24'].mean()
    print(f"  {s}: state_mean={state['R24'].mean():+.4f}, all_mean={sub['R24'].mean():+.4f}, LIFT={lift:+.4f}%")

# 6. Temporal sub-periods di TEST
print("\n--- 6. TEMPORAL SUB-PERIODS DI TEST (bulan) ---")
test=dc[dc['split']=='TEST']
if len(test)>0:
    test['month']=test.index.to_period('M')
    for m in sorted(test['month'].unique()):
        sub=test[test['month']==m]
        st=sub[sub['STATE']]
        if len(st)>0:
            print(f"  {m}: state_n={len(st):>5}, E[R24]={st['R24'].mean():+.4f}%, %pos={(st['R24']>0).mean()*100:.0f}%")

# 7. Price level shift
print("\n--- 7. PRICE LEVEL (BTC proxy, median close per split) ---")
btc=all_df[all_df['sym']=='BTCUSDT'].dropna(subset=['close','R24'])
for s in ['TRAIN','VAL','TEST']:
    sub=btc[btc['split']==s]
    if len(sub)==0: continue
    print(f"  {s}: median_close={sub['close'].median():.0f}, mean_R24={sub['R24'].mean():+.4f}%")

print("\n"+"="*70)
print("POST-MORTEM SELESAI")
print("="*70)
