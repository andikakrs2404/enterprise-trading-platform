#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-011 — Market Structure (System-Level State)
==================================================
PREREGISTERED: 3 hipotesis terpisah + context engine test
Failure criteria A-E (termasuk E: gross ≥ 20bps).

H1 — LEADERSHIP: siapa memimpin?
H2 — BREADTH: berapa luas partisipasi?
H3 — ROTATION: ke mana modal berpindah?

Pertanyaan utama: apakah market structure menjelaskan KAPAN
feature sebelumnya aktif/tidak aktif? (context engine)
"""
import json, os, random
import pandas as pd, numpy as np
random.seed(42); np.random.seed(42)

DATA='/home/rtk/Bot-Multi-Edge-metrics/data'
KDIR=DATA+'/klines'; MDIR=DATA+'/metrics'
OUT='/home/rtk/enterprise-trading-platform/layer5_alpha_engine/research'

def load(sym):
    k=os.path.join(KDIR,sym,'klines_1h.parquet')
    m=os.path.join(MDIR,sym,'metrics_1h.parquet')
    if not os.path.exists(k): return None
    df=pd.read_parquet(k)[['close','volume']].copy()
    df=df.rename_axis('ts').reset_index()
    df['ts']=pd.to_datetime(df['ts'],utc=True)
    df['ret']=df['close'].pct_change()
    df['ret24']=df['close'].pct_change(24)
    df['ret20d']=df['close'].pct_change(480)
    for h in [24,48,72]:
        df[f'R{h}']=(df['close'].shift(-h)/df['close']-1)*100
    df['above_ma20']=(df['close']>df['close'].rolling(480).mean()).astype(float)
    if os.path.exists(m):
        met=pd.read_parquet(m); met=met.rename_axis('ts').reset_index()
        met['ts']=pd.to_datetime(met['ts'],utc=True)
        df=df.merge(met[['ts','sum_open_interest']],on='ts',how='left')
    else: df['sum_open_interest']=np.nan
    df['oi_prev24']=df['sum_open_interest'].shift(24)
    df['vol_prev24']=df['volume'].shift(24)
    df['oi_growth']=df['sum_open_interest']/df['oi_prev24']-1
    df['vol_growth']=df['volume']/df['vol_prev24']-1
    df['sym']=sym
    return df

print("="*70)
print("STUDY-011 — MARKET STRUCTURE (System-Level State)")
print("H1 Leadership | H2 Breadth | H3 Rotation + Context Engine Test")
print("="*70)

frames={}
for sym in sorted(os.listdir(KDIR)):
    df=load(sym)
    if df is not None: frames[sym]=df
all_df=pd.concat(frames.values(),ignore_index=True).sort_values('ts').reset_index(drop=True)
ts_count=all_df.groupby('ts').size()
valid=ts_count[ts_count>=10].index
all_df=all_df[all_df['ts'].isin(valid)].copy()
all_df['year']=all_df['ts'].dt.year

# ================================================================
# MARKET STRUCTURE FEATURES (computed globally per timestamp)
# ================================================================
# % alt with positive R24
all_df['pos_ret24']=(all_df['ret24']>0).astype(float)
ts=all_df.groupby('ts')
breadth_pos=ts['pos_ret24'].apply(lambda x:x[~all_df.loc[x.index,'sym'].isin(['BTCUSDT','ETHUSDT'])].mean() if len(x)>0 else np.nan)

# --- H1: LEADERSHIP (need btc_ret24, eth_ret24, univ_med) ---
btc=all_df[all_df['sym']=='BTCUSDT'][['ts','ret24']].rename(columns={'ret24':'btc_ret24'})
eth=all_df[all_df['sym']=='ETHUSDT'][['ts','ret24']].rename(columns={'ret24':'eth_ret24'})
all_df=all_df.merge(btc,on='ts',how='left').merge(eth,on='ts',how='left')
univ_med=ts['ret24'].median().rename('univ_med')
all_df=all_df.merge(univ_med.reset_index(),on='ts',how='left')

# H1a: BTC leadership — BTC ret > universe median?
all_df['btc_leader']=(all_df['btc_ret24']>all_df['univ_med']).astype(float)
# H1b: ETH vs BTC strength
all_df['eth_vs_btc']=all_df['eth_ret24']-all_df['btc_ret24']
# H1c: BTC dominance proxy — BTC ret vs alt average
alt_mask=~all_df['sym'].isin(['BTCUSDT','ETHUSDT'])
alt_ret=all_df[alt_mask].groupby('ts')['ret24'].mean().rename('alt_avg_ret')
all_df=all_df.merge(alt_ret.reset_index(),on='ts',how='left')
all_df['btc_dom']=(all_df['btc_ret24']-all_df['alt_avg_ret'])

# --- H2: BREADTH ---
# % alt above MA20
breadth_alt=ts['above_ma20'].apply(lambda x:x[~all_df.loc[x.index,'sym'].isin(['BTCUSDT','ETHUSDT'])].mean() if len(x)>0 else np.nan)
breadth_alt=breadth_alt.rename('alt_breadth')
all_df=all_df.merge(breadth_alt.reset_index(),on='ts',how='left')
# % alt with positive R24
all_df['pos_ret24']=(all_df['ret24']>0).astype(float)
breadth_pos=ts['pos_ret24'].apply(lambda x:x[~all_df.loc[x.index,'sym'].isin(['BTCUSDT','ETHUSDT'])].mean() if len(x)>0 else np.nan)
breadth_pos=breadth_pos.rename('alt_pos_breadth')
all_df=all_df.merge(breadth_pos.reset_index(),on='ts',how='left')
# Breadth change (1d)
all_df['breadth_delta']=all_df.groupby('ts')['alt_breadth'].transform(lambda x:x)  # placeholder
all_df['breadth_delta']=all_df['alt_breadth'].diff(1)  # but this is per sym...

# Better: compute breadth as global per timestamp
bdf=all_df[['ts','alt_breadth']].drop_duplicates(subset='ts').sort_values('ts').reset_index(drop=True)
bdf['breadth_chg']=bdf['alt_breadth'].diff(24)  # 1d change in breadth
bdf['breadth_high']=bdf['alt_breadth'].rolling(168).mean()
all_df=all_df.merge(bdf[['ts','breadth_chg','breadth_high']],on='ts',how='left')

# --- H3: ROTATION ---
# Capital rotation: 7d momentum BTC vs ETH vs Alt
all_df['rot_btc_eth']=all_df['btc_ret24']-all_df['eth_ret24']  # >0: BTC leading
all_df['rot_eth_alt']=all_df['eth_ret24']-all_df['alt_avg_ret']  # >0: ETH leading
all_df['rot_btc_alt']=all_df['btc_ret24']-all_df['alt_avg_ret']  # >0: BTC leading over alt

# Filter and clean
all_df=all_df.dropna(subset=['ret24','R24','btc_ret24','alt_breadth'])
all_df['rs_rank']=ts['ret24'].rank(pct=True)
disp=ts['ret24'].agg(lambda x:x.quantile(0.9)-x.quantile(0.1))
disp_med=disp.median()
all_df['disp_state']=all_df['ts'].map(lambda x:'HIGH' if disp.get(x,0)>disp_med else 'LOW')
print(f"Clean rows: {len(all_df)}, sym: {len(all_df['sym'].unique())}")

# Non-overlap for temporal tests
all_df=all_df.sort_values(['sym','ts']).reset_index(drop=True)
all_df['sym_seq']=all_df.groupby('sym').cumcount()
dc_no=all_df[all_df['sym_seq']%72==0].copy()
print(f"Non-overlap: {len(dc_no)} rows")

def quintile_spread(df, col, target='R24', nq=5):
    """Rank col → quintile, return per-quintile means + spread."""
    tmp=df.copy()
    try:
        tmp['q']=pd.qcut(tmp[col],nq,labels=[f'Q{i}' for i in range(1,nq+1)])
    except ValueError:
        return None
    means={q:tmp[tmp['q']==q][target].mean() for q in [f'Q{i}' for i in range(1,nq+1)]}
    sp=means[f'Q{nq}']-means['Q1']
    return means,sp

# ================================================================
# H1: LEADERSHIP
# ================================================================
print("\n"+"="*70)
print("H1: LEADERSHIP — btc_dom, eth_vs_btc, rot_btc_eth, rot_btc_alt")
print("="*70)
for feat in ['btc_dom','eth_vs_btc','rot_btc_eth','rot_btc_alt']:
    r=quintile_spread(dc_no,feat)
    if r is None: print(f"  {feat}: cannot compute"); continue
    ms,sp=r
    print(f"  {feat}: Q1={ms['Q1']:+.4f}% Q5={ms['Q5']:+.4f}% spread={sp:+.4f}%",end='')
    print(f" {'>20bps' if abs(sp)*100>=20 else '<20bps'}")
    if sp*100>=20:
        # per year
        for yr in [2024,2025,2026]:
            sub=dc_no[dc_no['year']==yr]
            if len(sub)<100: continue
            r2=quintile_spread(sub,feat)
            if r2: print(f"    {yr}: spread={r2[1]:+.4f}%")

# ================================================================
# H2: BREADTH
# ================================================================
print("\n"+"="*70)
print("H2: BREADTH — alt_breadth, breadth_chg, alt_pos_breadth")
print("="*70)
for feat in ['alt_breadth','breadth_chg','alt_pos_breadth']:
    r=quintile_spread(dc_no,feat)
    if r is None: print(f"  {feat}: cannot compute"); continue
    ms,sp=r
    print(f"  {feat}: Q1={ms['Q1']:+.4f}% Q5={ms['Q5']:+.4f}% spread={sp:+.4f}%",end='')
    print(f" {'>20bps' if abs(sp)*100>=20 else '<20bps'}")
    if abs(sp)*100>=20:
        for yr in [2024,2025,2026]:
            sub=dc_no[dc_no['year']==yr]
            if len(sub)<100: continue
            r2=quintile_spread(sub,feat)
            if r2: print(f"    {yr}: spread={r2[1]:+.4f}%")

# ================================================================
# H3: ROTATION
# ================================================================
print("\n"+"="*70)
print("H3: ROTATION — rot_btc_eth, rot_eth_alt, rot_btc_alt")
print("="*70)
for feat in ['rot_btc_eth','rot_eth_alt','rot_btc_alt']:
    r=quintile_spread(dc_no,feat)
    if r is None: print(f"  {feat}: cannot compute"); continue
    ms,sp=r
    print(f"  {feat}: Q1={ms['Q1']:+.4f}% Q5={ms['Q5']:+.4f}% spread={sp:+.4f}%",end='')
    print(f" {'>20bps' if abs(sp)*100>=20 else '<20bps'}")

# ================================================================
# CONTEXT ENGINE TEST: Does market structure explain when RS works?
# ================================================================
print("\n"+"="*70)
print("CONTEXT ENGINE: RS spread (Q5-Q1 of Price RS) conditional on market structure")
print("="*70)
all_df['rs_q']=all_df.groupby('ts')['ret24'].rank(pct=True)
all_df['rs_q5']=pd.qcut(all_df['rs_q'],5,labels=['RS1','RS2','RS3','RS4','RS5'])
# For each market structure feature, split into regimes and test RS spread
for feat,threshold in [('btc_dom',None),('alt_breadth',None),('rot_btc_alt',None)]:
    print(f"\n  --- RS spread conditioned on {feat} ---")
    if threshold is None:
        # Use median split
        med=all_df[feat].median()
        regimes={'LOW':all_df[all_df[feat]<=med],'HIGH':all_df[all_df[feat]>med]}
    else:
        regimes={'LOW':all_df[all_df[feat]<=threshold],'HIGH':all_df[all_df[feat]>threshold]}
    for regime_name,sub in regimes.items():
        rs5=sub[sub['rs_q5']=='RS5']['R24'].mean()
        rs1=sub[sub['rs_q5']=='RS1']['R24'].mean()
        sp=rs5-rs1
        print(f"    {regime_name} (n={len(sub)}): RS5={rs5:+.4f}% RS1={rs1:+.4f}% spread={sp:+.4f}%")
    # Also check breadth quartile → RS spread
    if feat=='alt_breadth':
        for q in ['Q1','Q2','Q3','Q4','Q5']:
            try:
                tmp=all_df.copy()
                tmp['bq']=pd.qcut(tmp['alt_breadth'],5,labels=['Q1','Q2','Q3','Q4','Q5'])
                sub=tmp[tmp['bq']==q]
                rs5=sub[sub['rs_q5']=='RS5']['R24'].mean()
                rs1=sub[sub['rs_q5']=='RS1']['R24'].mean()
                sp=rs5-rs1
                print(f"    breadth_q={q}: RS spread={sp:+.4f}% (n={len(sub)})")
            except: pass

# ================================================================
# DOUBLE-SORT: market structure × Price RS (independence)
# ================================================================
print("\n"+"="*70)
print("DOUBLE-SORT: btc_dom × Price RS → R24 (independence)")
print("="*70)
all_df['btc_dom_q']=pd.qcut(all_df.groupby('ts')['btc_dom'].rank(pct=True),5,
                            labels=['Q1','Q2','Q3','Q4','Q5'])
mat=np.zeros((5,5))
for i,qv in enumerate(['Q1','Q2','Q3','Q4','Q5']):
    for j,qr in enumerate(['RS1','RS2','RS3','RS4','RS5']):
        m=(all_df['btc_dom_q']==qv)&(all_df['rs_q5']==qr)
        mat[i,j]=all_df.loc[m,'R24'].mean() if m.sum()>0 else np.nan
print(f"  {'':>8}{'RS1':>8}{'RS2':>8}{'RS3':>8}{'RS4':>8}{'RS5':>8}")
for i,qv in enumerate(['Q1','Q2','Q3','Q4','Q5']):
    print(f"  {qv:>6}  {mat[i,0]:>+8.4f}{mat[i,1]:>+8.4f}{mat[i,2]:>+8.4f}{mat[i,3]:>+8.4f}{mat[i,4]:>+8.4f}")
cond_sp=mat[4,2]-mat[0,2]  # btc_dom spread conditional on RS neutral
print(f"  Conditional on RS neutral: btc_dom spread = {cond_sp:+.4f}%")
print(f"  → {'INDEPENDENT' if abs(cond_sp)>0.005 else 'PROXY RS'}")

# ================================================================
# CONTEXT ENGINE: OI_share_7d conditional on breadth (from STUDY-008)
# ================================================================
print("\n"+"="*70)
print("CONTEXT ENGINE: OI_share_7d × alt_breadth (can breadth explain OI_share?)")
print("="*70)
all_df['oi_share_rank']=all_df.groupby('ts')['oi_growth'].rank(pct=True)
all_df['oi_q']=pd.qcut(all_df['oi_share_rank'],5,labels=['Q1','Q2','Q3','Q4','Q5'])
for bq in ['Q1','Q2','Q3','Q4','Q5']:
    try:
        tmp=all_df.copy()
        tmp['bq']=pd.qcut(tmp['alt_breadth'],5,labels=['Q1','Q2','Q3','Q4','Q5'])
        sub=tmp[tmp['bq']==bq]
        oiq5=sub[sub['oi_q']=='Q5']['R24'].mean()
        oiq1=sub[sub['oi_q']=='Q1']['R24'].mean()
        sp=oiq5-oiq1
        print(f"  breadth_q={bq}: OI_share spread={sp:+.4f}% (n={len(sub)})")
    except: pass

# ================================================================
# NET AFTER COST (for features >20bps gross)
# ================================================================
print("\n"+"="*70)
print("NET AFTER COST (for surviving features, non-overlap R24)")
print("="*70)
print("  (Features >20bps gross auto-pass criterion E)")
print("  Fee sensitivity for context engine RS spread:")

for feat_name,feat_col in [('btc_dom','btc_dom'),('alt_breadth','alt_breadth'),('rot_btc_alt','rot_btc_alt')]:
    if feat_col not in all_df.columns: continue
    med=all_df[feat_col].median()
    sub_high=all_df[all_df[feat_col]>med]
    sub_low=all_df[all_df[feat_col]<=med]
    sp_high=sub_high[sub_high['rs_q5']=='RS5']['R24'].mean()-sub_high[sub_high['rs_q5']=='RS1']['R24'].mean()
    sp_low=sub_low[sub_low['rs_q5']=='RS5']['R24'].mean()-sub_low[sub_low['rs_q5']=='RS1']['R24'].mean()
    print(f"  {feat_name} HIGH regime → RS spread={sp_high:+.4f}%")
    for fee in [8,12,16]:
        net=sp_high-fee*2/100
        print(f"    Fee {fee}bps: net={net:+.4f}% ({net*100:+.1f}bps)")

# ================================================================
# SAVE
# ================================================================
report={
    'study':'STUDY-011-MARKET-STRUCTURE','preregistered':True,
    'hypotheses':['H1 Leadership','H2 Breadth','H3 Rotation'],
    'context_engine_test':'RS spread conditional on market structure',
    'failure_criteria':'A-D + E: gross < 20bps auto-reject'
}
with open(os.path.join(OUT,'STUDY-011_MARKET_STRUCTURE.json'),'w') as f:
    json.dump(report,f,indent=2,default=str)
print(f"\nSaved: research/STUDY-011_MARKET_STRUCTURE.json")
print("STUDY-011 SELESAI")
print("="*70)
