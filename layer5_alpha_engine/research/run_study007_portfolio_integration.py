#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-007 — PORTFOLIO INTEGRATION STUDY (VECTORIZED, CEPAT)
============================================================
Incremental value test: Apakah Cross-Sectional RS memberi value di atas baseline?

MEKANISME WEIGHTING (DIKUNCI SEBELUM HASIL — post-hoc dilarang):
  - B1 Trend:        long close>EMA24, short close<EMA24, equal-weight
  - B2 MeanRev:      long z24<0, short z24>0, equal-weight
  - B1+RSweight:     arah baseline, bobot w = 0.5 + 0.5*rs_rank (linear)
  - B2+RSweight:     arah baseline, bobot w = 0.5 + 0.5*rs_rank
  - RS_Standalone:   long top 50% RS, short bottom 50%, equal-weight
FEE = 8bps round-trip.
Portfolio = mean over symbols per bar (equal exposure).
Ret = position (prev bar) * symbol ret (avoid lookahead: pos shifted)
"""
import json, os, random
import pandas as pd, numpy as np
random.seed(42); np.random.seed(42)

DATA='/home/rtk/Bot-Multi-Edge-metrics/data'
KDIR=DATA+'/klines'
OUT='/home/rtk/enterprise-trading-platform/layer5_alpha_engine/research'
FEE=0.0008

def load(sym):
    k=os.path.join(KDIR,sym,'klines_1h.parquet')
    if not os.path.exists(k): return None
    df=pd.read_parquet(k)[['open','high','low','close','volume']].copy()
    df.index=pd.to_datetime(df.index,utc=True)
    df['sym']=sym
    df['ema24']=df['close'].ewm(span=24,adjust=False).mean()
    df['ret24']=df['close'].pct_change(24)
    df['mean24']=df['close'].rolling(24).mean()
    df['std24']=df['close'].rolling(24).std()
    df['z24']=(df['close']-df['mean24'])/df['std24']
    df['ret']=df['close'].pct_change()
    return df

print("="*70)
print("STUDY-007 — PORTFOLIO INTEGRATION (VECTORIZED)")
print("FEE=8bps. Weighting pre-frozen. Incremental info test.")
print("="*70)

syms=sorted(os.listdir(KDIR))
frames=[load(s) for s in syms]
frames=[f for f in frames if f is not None]
all_df=pd.concat(frames).dropna(subset=['ema24','ret24','z24','ret']).sort_index()
print(f"Rows: {len(all_df)}, sym: {len(syms)}")

# Cross-sectional RS rank per timestamp
all_df['rs_rank']=all_df.groupby(all_df.index)['ret24'].rank(pct=True)
# Only timestamps with enough symbols
ts_count=all_df.groupby(all_df.index).size()
all_df=all_df[all_df.index.isin(ts_count[ts_count>=10].index)].sort_index()
print(f"Rows after >=10 sym/ts: {len(all_df)}")

# ================================================================
# COMPUTE POSITIONS (vectorized, per symbol per bar)
# ================================================================
# Position decided at bar t-1, earns ret at bar t. Shift position by 1.
df=all_df.copy()

# B1 Trend
df['pos_b1']=np.where(df['close']>df['ema24'],1.0,-1.0)
# B2 MeanRev
df['pos_b2']=np.where(df['z24']<0,1.0,-1.0)
# RSweight for B1: direction preserved, weight by rs_rank
df['pos_b1rsw']=np.where(df['close']>df['ema24'],1.0,-1.0)*(0.5+0.5*df['rs_rank'])
# RSweight for B2
df['pos_b2rsw']=np.where(df['z24']<0,1.0,-1.0)*(0.5+0.5*df['rs_rank'])
# RS standalone: long top50 short bottom50 (per ts, need per-ts threshold)
df['rs_top']=df['rs_rank']>=0.5
df['pos_rs']=np.where(df['rs_top'],1.0,-1.0)

# Held position (previous bar) -> shift per symbol
for col in ['pos_b1','pos_b2','pos_b1rsw','pos_b2rsw','pos_rs']:
    df[f'hold_{col}']=df.groupby('sym')[col].shift(1)

# ================================================================
# PORTFOLIO RETURN PER BAR (mean over symbols at same timestamp)
# ================================================================
# contribution = hold_position * ret
for col in ['pos_b1','pos_b2','pos_b1rsw','pos_b2rsw','pos_rs']:
    hold=df[f'hold_{col}']
    contrib=hold*df['ret']
    df[f'contrib_{col}']=contrib
    # turnover: |pos_t - pos_{t-1}|, fee applies on change
    df[f'turn_{col}']=(df[col]-df.groupby('sym')[col].shift(1)).abs()

# Drop NaN rows (first bar per symbol after shift) BEFORE averaging
df=df.dropna(subset=['contrib_pos_b1','contrib_pos_b2','contrib_pos_rs'])

# Mean over symbols per timestamp
def portfolio(prefix):
    g=df.groupby(df.index)[[f'contrib_{prefix}',f'turn_{prefix}']].mean()
    return g[f'contrib_{prefix}'], g[f'turn_{prefix}']

print("\n"+"="*70)
print("PORTFOLIO METRICS (net of 8bps fee, hourly)")
print("="*70)
names={'pos_b1':'B1_Trend','pos_b2':'B2_MeanRev','pos_b1rsw':'B1+RSweight',
       'pos_b2rsw':'B2+RSweight','pos_rs':'RS_Standalone'}
PER_DAY=24; DAYS_YEAR=365

def metrics(contrib, turn):
    gross=contrib-turn*FEE  # net
    mean=gross.mean(); std=gross.std()
    sharpe=mean/std*np.sqrt(PER_DAY*DAYS_YEAR) if std>0 else 0
    cum=(1+contrib).cumprod()  # gross cumulative for maxdd (or net)
    netcum=(1+gross).cumprod()
    dd=(netcum/netcum.cummax()-1).min()
    return mean,std,sharpe,dd,turn.mean()

rows={}
for prefix,name in names.items():
    c,t=portfolio(prefix)
    mean,std,sharpe,dd,turn=metrics(c,t)
    rows[prefix]={'c':c,'t':t,'mean':mean,'std':std,'sharpe':sharpe,'dd':dd,'turn':turn}
    print(f"  {name:<18} Sharpe={sharpe:>+8.2f}  MaxDD={dd:>+8.4f}  "
          f"Net/bar={mean*100:>+8.4f}%  Turnover={turn*100:>7.3f}%/bar")

# ================================================================
# INCREMENTAL VALUE
# ================================================================
print("\n"+"="*70)
print("INCREMENTAL VALUE: baseline vs baseline+RSweight")
print("="*70)
for base,rs in [('pos_b1','pos_b1rsw'),('pos_b2','pos_b2rsw')]:
    bn=names[base]; rn=names[rs]
    corr=np.corrcoef(rows[base]['c'],rows[rs]['c'])[0,1]
    dsharpe=rows[rs]['sharpe']-rows[base]['sharpe']
    ddd=rows[rs]['dd']-rows[base]['dd']
    dnet=rows[rs]['mean']-rows[base]['mean']
    dturn=rows[rs]['turn']-rows[base]['turn']
    print(f"\n  {bn} → {rn}:")
    print(f"    Corr(returns)={corr:.3f}")
    print(f"    ΔSharpe: {dsharpe:+.2f}")
    print(f"    ΔMaxDD: {ddd:+.4f}")
    print(f"    ΔNet/bar: {dnet*100:+.4f}%")
    print(f"    ΔTurnover: {dturn*100:+.4f}%/bar")
    if rows[rs]['sharpe']>rows[base]['sharpe'] and rows[rs]['dd']>rows[base]['dd']:
        print(f"    → RS INCREASES Sharpe & REDUCES drawdown: incremental value POSITIVE")
    elif rows[rs]['sharpe']>rows[base]['sharpe']:
        print(f"    → RS increases Sharpe (dd not improved): mixed")
    else:
        print(f"    → RS does NOT improve Sharpe: incremental value NOT established")

# ================================================================
# RS_Standalone vs baselines (diversification via low correlation?)
# ================================================================
print("\n"+"="*70)
print("CROSS-PORTFOLIO CORRELATION (diversification check)")
print("="*70)
port_order=['pos_b1','pos_b2','pos_b1rsw','pos_b2rsw','pos_rs']
for i,a in enumerate(port_order):
    for b in port_order[i+1:]:
        corr=np.corrcoef(rows[a]['c'],rows[b]['c'])[0,1]
        print(f"  {names[a]:<18} vs {names[b]:<18}: corr={corr:+.3f}")

# Save
report={
    'study':'STUDY-007-PORTFOLIO-INTEGRATION','parent':'STUDY-006',
    'fee_bps':8,
    'weighting_PRE_FROZEN':{
        'RSweight':'w=0.5+0.5*rs_rank, direction preserved from baseline',
        'RS_Standalone':'long top50%, short bottom50%, equal-weight',
        'rebalance':'per bar (hourly)','leverage':1.0,'normalization':'mean over symbols'},
    'metrics':{names[k]:{'sharpe_ann':round(rows[k]['sharpe'],2),'maxdd':round(rows[k]['dd'],4),
        'net_per_bar_pct':round(rows[k]['mean']*100,4),'turnover_pct':round(rows[k]['turn']*100,3)}
        for k in port_order},
    'incremental':{f'{names[b]}_over_{names[a]}':{'corr':round(float(np.corrcoef(rows[a]['c'],rows[b]['c'])[0,1]),3),
        'd_sharpe':round(rows[b]['sharpe']-rows[a]['sharpe'],2),
        'd_maxdd':round(rows[b]['dd']-rows[a]['dd'],4)} for a,b in [('pos_b1','pos_b1rsw'),('pos_b2','pos_b2rsw')]},
    'guardrails':['no_posthoc','net_after_cost','weighting_pre_frozen'],
    'label':'Portfolio Integration Test — incremental info, bukan edge selection'}
with open(os.path.join(OUT,'STUDY-007_PORTFOLIO_INTEGRATION.json'),'w') as f:
    json.dump(report,f,indent=2,default=str)
print("\nSaved: research/STUDY-007_PORTFOLIO_INTEGRATION.json")
print("STUDY-007 SELESAI")
print("="*70)
