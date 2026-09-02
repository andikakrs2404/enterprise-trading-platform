#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-006 — Cross-Sectional Relative Strength (EXPLORATORY / NON-ALPHA)
Phase A: Phenomenon Discovery

Prinsip: Relative ranking, bukan directional prediction absolut.
Tidak perlu tahu pasar naik/turun. Cukup tahu siapa yang lebih kuat.

Tujuan Phase A:
1. Apakah ranking momentum prediktif untuk forward return?
2. Apakah leaders continue atau revert?
3. Apakah phenomena stabil lintas time windows?
"""
import json, os, random, statistics
import pandas as pd, numpy as np
random.seed(42); np.random.seed(42)

DATA='/home/rtk/Bot-Multi-Edge-metrics/data'
KDIR=DATA+'/klines'
OUT='/home/rtk/enterprise-trading-platform/layer5_alpha_engine/research'
os.makedirs(OUT, exist_ok=True)

def load(sym):
    k=os.path.join(KDIR,sym,'klines_1h.parquet')
    if not os.path.exists(k): return None
    df=pd.read_parquet(k)[['open','high','low','close','volume']].copy()
    df.index=pd.to_datetime(df.index,utc=True)
    return df

print("="*70)
print("STUDY-006 — CROSS-SECTIONAL RELATIVE STRENGTH (EXPLORATORY)")
print("Phase A: Ranking-based phenomenon, bukan directional")
print("="*70)

syms=sorted(os.listdir(KDIR))
frames=[]
for sym in syms:
    df=load(sym)
    if df is None: continue
    df['sym']=sym
    df['ret_1h']=df['close'].pct_change()
    df['ret_6h']=df['close'].pct_change(6)
    df['ret_24h']=df['close'].pct_change(24)
    df['ret_168h']=df['close'].pct_change(168)  # 7 days
    df['vol_24h']=df['close'].pct_change().rolling(24).std()
    df['vol_168h']=df['close'].pct_change().rolling(168).std()
    df['volume_ratio']=df['volume']/df['volume'].rolling(168).mean()
    for h in [1,6,24,168]: df[f'R{h}']=(df['close'].shift(-h)/df['close']-1)*100
    frames.append(df)

all_df=pd.concat(frames)
print(f"Total rows: {len(all_df)}, Symbols: {len(syms)}")

# Drop rows without enough history
all_df=all_df.dropna(subset=['ret_168h','vol_168h','R1','R6','R24','R168'])
print(f"Clean rows: {len(all_df)}")

# ================================================================
# 1. CROSS-SECTIONAL RANKING AT EACH TIMESTAMP
# ================================================================
print("\n"+"="*70)
print("1. CROSS-SECTIONAL RANKING METHODOLOGY")
print("="*70)

# Untuk setiap timestamp, rank semua symbol berdasarkan momentum
# Pastikan ada minimum 5 symbol aktif per timestamp
ts_counts=all_df.groupby(all_df.index).size()
active_ts=ts_counts[ts_counts>=5].index
df_active=all_df[all_df.index.isin(active_ts)]
print(f"Timestamps dengan ≥5 symbol aktif: {len(active_ts)}")

# Rank per timestamp untuk setiap momentum measure
for col in ['ret_1h','ret_6h','ret_24h','ret_168h']:
    df_active[col+'_rank']=df_active.groupby(df_active.index)[col].rank(pct=True)
print("Ranking computed: ret_1h_rank, ret_6h_rank, ret_24h_rank, ret_168h_rank")

# ================================================================
# 2. QUINTILE ANALYSIS: Rank → Forward Return
# ================================================================
print("\n"+"="*70)
print("2. QUINTILE ANALYSIS: Momentum Rank → Forward Return")
print("="*70)

# Untuk 4 momentum horizons, hitung E[R] per quintile
for rank_col,mom_label in [('ret_24h_rank','24h_mom'),('ret_168h_rank','7d_mom'),('ret_6h_rank','6h_mom'),('ret_1h_rank','1h_mom')]:
    df_active['quintile']=pd.qcut(df_active[rank_col],5,labels=['Q1_worst','Q2','Q3','Q4','Q5_best'])
    print(f"\n  --- {mom_label} quintile → forward return ---")
    for q in ['Q1_worst','Q2','Q3','Q4','Q5_best']:
        sub=df_active[df_active['quintile']==q]
        r1=sub['R1'].mean(); r6=sub['R6'].mean(); r24=sub['R24'].mean()
        pos=(sub['R24']>0).mean()*100
        print(f"  {q:>10}: n={len(sub):>8}, R1={r1:>+8.4f}%, R6={r6:>+8.4f}%, R24={r24:>+8.4f}%, %pos={pos:.0f}%")
    # Monotonicity check
    q_means=[df_active[df_active['quintile']==q]['R24'].mean() for q in ['Q1_worst','Q2','Q3','Q4','Q5_best']]
    mono=sum(1 for i in range(len(q_means)-1) if q_means[i]<=q_means[i+1])
    spread=q_means[-1]-q_means[0]
    print(f"  Spread (Q5-Q1) R24: {spread:+.4f}%, Monotonic: {mono}/4 steps")
    df_active.drop('quintile',axis=1,inplace=True)

# ================================================================
# 3. LEADER vs LAGGARD: 24h momentum
# ================================================================
print("\n"+"="*70)
print("3. LEADER vs LAGGARD (ret_24h top 20% vs bottom 20%)")
print("="*70)

df_active['is_leader']=df_active['ret_24h_rank']>=0.8
df_active['is_laggard']=df_active['ret_24h_rank']<=0.2

for label,col in [('LEADER','is_leader'),('LAGGARD','is_laggard'),('MID','ret_24h_rank between 0.2-0.8')]:
    if label=='MID':
        sub=df_active[(df_active['ret_24h_rank']>0.2)&(df_active['ret_24h_rank']<0.8)]
    else:
        sub=df_active[df_active[col]]
    if len(sub)==0: continue
    print(f"  {label:>7}: n={len(sub):>8}, R1={sub['R1'].mean():>+.4f}%, R6={sub['R6'].mean():>+.4f}%, R24={sub['R24'].mean():>+.4f}%")

# Leader continuation: apakah leader di t tetap leader di t+24?
# (Ini perlu shift, tapi untuk Phase A cukup forward return saja)

# ================================================================
# 4. REVERSAL vs CONTINUATION: Leader-forward
# ================================================================
print("\n"+"="*70)
print("4. REVERSAL vs CONTINUATION CHECK")
print("="*70)
leaders=df_active[df_active['is_leader']]
laggards=df_active[df_active['is_laggard']]

leader_cont=leaders['R24'].mean()
laggard_rev=laggards['R24'].mean()
print(f"  Leader R24 (continuation): {leader_cont:+.4f}%")
print(f"  Laggard R24 (reversal check): {laggard_rev:+.4f}%")
print(f"  Leader-Laggard spread: {leader_cont-laggard_rev:+.4f}%")
if leader_cont>laggard_rev:
    print(f"  → Continuation pattern: leaders mengungguli laggards")
elif leader_cont<laggard_rev:
    print(f"  → Reversal pattern: laggards mengungguli leaders (mean reversion)")
else:
    print(f"  → Tidak ada preferensi")

# ================================================================
# 5. VOLATILITY-ADJUSTED RANKING
# ================================================================
print("\n"+"="*70)
print("5. VOLATILITY-ADJUSTED MOMENTUM (ret/vol)")
print("="*70)
df_active['mom_sharpe_24h']=df_active['ret_24h']/df_active['vol_24h']
df_active['mom_sharpe_168h']=df_active['ret_168h']/df_active['vol_168h']

for col,label in [('mom_sharpe_24h','24h_sharpe'),('mom_sharpe_168h','7d_sharpe')]:
    df_active[f'{col}_rank']=df_active.groupby(df_active.index)[col].rank(pct=True)
    df_active['q']=pd.qcut(df_active[f'{col}_rank'],5,labels=['Q1','Q2','Q3','Q4','Q5'])
    print(f"\n  --- {label} quintile → R24 ---")
    for q in ['Q1','Q2','Q3','Q4','Q5']:
        sub=df_active[df_active['q']==q]
        print(f"  {q}: n={len(sub):>8}, R24={sub['R24'].mean():>+.4f}%, %pos={(sub['R24']>0).mean()*100:.0f}%")
    df_active.drop('q',axis=1,inplace=True)
    df_active.drop(f'{col}_rank',axis=1,inplace=True)

# ================================================================
# 6. CROSS-SECTIONAL DISPERSION
# ================================================================
print("\n"+"="*70)
print("6. CROSS-SECTIONAL DISPERSION (return spread per timestamp)")
print("="*70)
# Untuk setiap timestamp: max ret_24h - min ret_24h di antara symbol aktif
dispersion=all_df.groupby(all_df.index)['ret_24h'].agg(lambda x: x.quantile(0.9)-x.quantile(0.1))
print(f"  Cross-sectional IQR(10-90) of 24h return:")
print(f"  Mean: {dispersion.mean():.4f}%, Median: {dispersion.median():.4f}%")
print(f"  P10: {dispersion.quantile(.1):.4f}%, P90: {dispersion.quantile(.9):.4f}%")

# Apakah dispersion prediktif? (high dispersion → momentum kuat?)
high_disp=dispersion[dispersion>dispersion.quantile(.75)].index
low_disp=dispersion[dispersion<dispersion.quantile(.25)].index
# Rata-rata momentum spread di high vs low dispersion
# ================================================================
for dts,name in [(high_disp,'HIGH_dispersion'),(low_disp,'LOW_dispersion')]:
    sub=df_active[df_active.index.isin(dts)&df_active['is_leader']]
    sub_l=df_active[df_active.index.isin(dts)&df_active['is_laggard']]
    if len(sub)>0 and len(sub_l)>0:
        spread_d=sub['R24'].mean()-sub_l['R24'].mean()
        print(f"  {name}: leader-Laggard R24 spread = {spread_d:+.4f}%, n_leader={len(sub)}, n_laggard={len(sub_l)}")

# 7. NEGATIVE FINDINGS (wajib)
# ================================================================
print("\n"+"="*70)
print("7. NEGATIVE FINDINGS")
print("="*70)
print("  1. Cross-sectional analysis butuh minimum 5+ symbol aktif — beberapa timestamp mungkin sparse")
print("  2. Sector classification belum diterapkan (semua symbol treated sama)")
print("  3. Volume & liquidity tidak diferensiasi (low-vol small-cap bisa dominasi ranking)")
print("  4. Regime interaction belum diuji")
print("  5. Temporal stability belum dicek (FIRST vs SECOND half)")

# ================================================================
# SAVE
# ================================================================
report={
    'study':'STUDY-006-CROSS-SECTIONAL-RS','status':'EXPLORATORY/NON-ALPHA',
    'n_symbols':len(syms),'n_rows':len(all_df),'n_active_ts':len(active_ts),
    'label':'Observed Phenomenon (Unregistered)',
    'note':'Phase A ranking-based. Belum ada sector classification. Bukan alpha.'}
with open(os.path.join(OUT,'STUDY-006_CROSS_SECTIONAL_RS.json'),'w') as f:
    json.dump(report,f,indent=2,default=str)
print("\nSaved: research/STUDY-006_CROSS_SECTIONAL_RS.json")
print("STUDY-006 Phase A SELESAI")
print("="*70)
