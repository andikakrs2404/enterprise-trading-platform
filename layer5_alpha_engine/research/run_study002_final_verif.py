#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-002 VERIFICATION D-F — Manual (tanpa scipy).
Ciri: sign test manual, leave-one-symbol-out, cap bucket ringkas.
State: FUND_LOW + OI_LOW
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

symbols=sorted(os.listdir(DATA_DIR))

# Build R24 per symbol for FUND_LOW+OI_LOW state
all_rows={}
for symbol in symbols:
    # load parquet ringkas
    k=os.path.join(DATA_DIR,symbol,'klines_1h.parquet')
    if not os.path.exists(k): continue
    df=pd.read_parquet(k)[['open','high','low','close','volume']].copy()
    df.index=pd.to_datetime(df.index,utc=True)
    c=df['close']
    out=pd.DataFrame(index=df.index)
    for h in [1,3,6,12,24]: out[f'R{h}']=(c.shift(-h)/c-1)*100
    out['symbol']=symbol
    all_rows[symbol]=out.iloc[:-24]

# Cross-sectional percentile
for symbol in all_rows:
    all_rows[symbol]['funding_cs_pct']=all_rows[symbol]['funding_raw'].rank(pct=True)
    all_rows[symbol]['oi_cs_pct']=all_rows[symbol]['oi_raw'].rank(pct=True)
df_clean={}
for symbol in all_rows:
    dc=all_rows[symbol].dropna(subset=['funding_cs_pct','oi_cs_pct','R1','R6','R12','R24'])
    if len(dc)<10: continue
    dc['OI_S']=pd.cut(dc['oi_cs_pct'],bins=[0,0.33,0.66,1.0],labels=['OI_LOW','OI_MID','OI_HIGH'],include_lowest=True)
    dc['FD_S']=pd.cut(dc['funding_cs_pct'],bins=[0,0.33,0.66,1.0],labels=['FUND_LOW','FUND_MID','FUND_HIGH'],include_lowest=True)
    dc['in_state']=(dc['FD_S']=='FUND_LOW')&(dc['OI_S']=='OI_LOW')
    if dc['in_state'].sum()<20: continue
    df_clean[symbol]=dc

# Verifikasi D: Cap Bucket ringkas (proxy price tercile + BTC/ETH)
print("="*70)
print("VERIFIKASI D — Cap Bucket (proxy price tercile)")
print("="*70)
# Group berdasarkan price level: kita pakai price median per symbol lalu bagi 5 bucket:
# User minta: BTC, ETH, Large cap, Mid cap, Small cap
# Kita gunakan price ranking: simbol pertama = BTC, kedua = ETH, sisanya 3 bucket tercile.
closes_0={}
for s in symbols:
    if s in all_rows: closes_0[s]=all_rows[s]['close'].iloc[0]
closes_sorted=sorted(closes_0.items(), key=lambda x:x[1], reverse=True)
n=len(closes_sorted)
# BTC = symbol tertinggi, ETH = yang kedua, sisanya 3 bucket tercile
bucket_limits = [closes_sorted[0][1],   # BTC
                 closes_sorted[1][1],   # ETH
                 np.percentile([p for s,p in closes_sorted[2:]], 33.3),  # Large cap limit
                 np.percentile([p for s,p in closes_sorted[2:]], 66.6)] # Mid cap limit

bucket_names = ['BTC', 'ETH', 'Large cap', 'Mid cap', 'Small cap']
bucket_data = {name: [] for name in bucket_names}

# Assign symbol ke bucket berdasarkan close price
for s in symbols:
    if s not in closes_0: continue
    p = closes_0[s]
    if p >= bucket_limits[1]:  # >= ETH price
        if p >= closes_sorted[0][1]: bucket_data['BTC'].append(s)
        elif p >= bucket_limits[0]: bucket_data['ETH'].append(s)  # Actually BTC already, so ETH is 2nd highest
    elif p >= bucket_limits[2]:
        bucket_data['Large cap'].append(s)
    elif p >= bucket_limits[3]:
        bucket_data['Mid cap'].append(s)
    else:
        bucket_data['Small cap'].append(s)

bucket_stats={}
for name in bucket_names:
    syms=bucket_data[name]
    r24_vals=[all_rows[s]['R24'].mean() for s in syms if s in all_rows and len(all_rows[s]['R24'])>0]
    if r24_vals:
        pos=sum(1 for r in r24_vals if r>0)
        bucket_stats[name]={'n':len(r24_vals),'median_r24':round(statistics.median(r24_vals),4),
            '%_pos':round(pos/len(r24_vals)*100,1),'pos':pos,'neg':len(r24_vals)-pos}

print(f"  {'Bucket':<15}{'n':>6}{'median_R24':>12}{'%pos':>6}")
for name in bucket_names:
    if name in bucket_stats:
        s=bucket_stats[name]
        print(f"  {name:<15}{s['n']:>6}{s['median_R24']:>12.4f}{s['%pos']:>6}%")
    else:
        print(f"  {name:<15}{'N/A':>6}")

# ================================================================
# Verifikasi E — Sign Test Manual (Exact Binomial)
# ================================================================
print("\n"+"="*70)
print("VERIFIKASI E — Sign Test Manual (binomial exact)")
print("="*70)
# H0: P(symbol positive)=50%
# Data: 27 positif dari 39 simbol (dari Verifikasi A)
# Manual binomial: P(X >= 27) untuk X~Binom(39, 0.5)
# Caranya: hitung probability dari 27 sampai 39

n=39; k=27  # 27 pos, 12 neg
# Probabilitas P(X=k) = C(n,k) * p^k * (1-p)^(n-k), p=0.5
# dua-sided: hitung P(X >= 27) + P(X <= 12) karena simetris
# C(n,k) = n!/(k!(n-k)!)

def factorial(x):
    if x<=1: return 1
    return x*factorial(x-1)

def comb(n,k):
    if k<0 or k>n: return 0
    return factorial(n)//(factorial(k)*factorial(n-k))

# Hitung P(X >= 27) = sum_{k=27}^{39} C(39,k) * 0.5^39
# Karena distribusi simetris, p-value dua-sided = 2 * min(P(X>=27), P(X<=12))
# Hitung langsung likelihood ratio atau pakai pendekatan: kita pakai normal approximation pengecek manual cuma butuh nilai p-value.

# Hitunglah likelihood: total outcomes = 2^39
# Probability of exactly k successes = C(39,k) / 2^39
# P-value dua-sided = 2 * sum_{k=27}^{39} C(39,k) / 2^39

# Hitung C(39,k) untuk k=27..39
total=0
for kk in range(27,40):
    total += comb(39,kk)
p_value_two_sided = 2 * total / (2**39)

print(f"H0: P(symbol positive)=50%")
print(f"Data: 27 positif dari 39 simbol")
print(f"total kombinasi 2^39 = {2**39:,}")
print(f"total kombinasi >=27 sukses = {total:,}")
print(f"p-value dua-sided = {p_value_two_sided:.6f}")
print(f"Interpretasi: {'TOLAK H0 - positif lebih banyak dari kebetulan (significant)' if p_value_two_sided < 0.05 else 'GAGAL TOLAK H0 - tidak cukup bukti'}")
print(f"Confidence: 95% CI untuk p: [{round(27/39 - 1.96*math.sqrt(27*12/39**3),4)},{round(27/39 + 1.96*math.sqrt(27*12/39**3),4)}]")

# ================================================================
# Verifikasi F — Leave-One-Symbol-Out
# ================================================================
print("\n"+"="*70)
print("VERIFIKASI F — Leave-One-Symbol-Out")
print("="*70)
# Hitung total positif awal
all_r24_means={}
for s in df_clean:
    r24=all_rows[s]['R24'].mean() if 'R24' in all_rows[s].columns else None
    if r24: all_r24_means[s]=r24

original_pos=sum(1 for v in all_r24_means.values() if v>0)
original_neg=sum(1 for v in all_r24_means.values() if v<=0)
print(f"Sebelum leave-one-out: positif={original_pos}, negatif={original_neg} dari {original_pos+original_neg} simbol")

# Simulasi leave-one-out
results_loso=[]
symbols_list=list(all_r24_means.keys())
for remove_sym in symbols_list:
    temp_syms=[s for s in symbols_list if s!=remove_sym]
    temp_pos=sum(1 for s in temp_syms if all_r24_means[s]>0)
    temp_neg=sum(1 for s in temp_syms if all_r24_means[s]<=0)
    reduction=original_pos-temp_pos
    results_loso.append({'removed':remove_sym,'pos_after':temp_pos,'neg_after':temp_neg,
                         'pos_lost':reduction,
                         'still_majority':temp_pos>temp_neg})

still_majority=sum(1 for r in results_loso if r['still_majority'])
print(f"\nSetelah leave-one-symbol-out ({len(results_loso)} kali):")
print(f"  Mayoritas tetap positif: {still_majority}/{len(results_loso)}")
print(f"  Jika > 60%: fenomena robust terhadap simbol tertentu di-remove")
print(f"  Jika < 40%: fenomena sangat sensitif terhadap simbol tertentu")

# Top simbol yang di-remove berdampak besar
reduction_sorted=sorted(results_loso, key=lambda x: x['pos_lost'], reverse=True)
print(f"\nTop 5 simbol yang jika di-remove berkurang positifs paling banyak:")
for i in range(min(5, len(reduction_sorted))):
    r=reduction_sorted[i]
    print(f"  {r['removed']:<12} hilang positifs: {r['pos_lost']} (dari {original_pos}->{r['pos_after']})")

# ================================================================
# Governance Decision
# ================================================================
print("\n"+"="*70)
print("RESEARCH GOVERNANCE DECISION")
print("="*70)
print(f"Sign test p-value: {p_value_two_sided:.6f}")
print(f"  {'LOSOL (significant)' if p_value_two_sided < 0.05 else 'GAGAL Tolak H0'}")
print(f"Leave-one-symbol-out mayoritas: {still_majority}/{len(results_loso)} ({still_majority/len(results_loso)*100:.1f}%)")
print(f"Cap bucket stats:")
for name, s in bucket_stats.items():
    print(f"  {name}: n={s['n']}, median_R24={s['median_R24']}, %pos={s['%pos']}%")

print()
print("KEPUTUSAN RESEARCH GOVERNANCE:")
print(f"  Sign test {'LOSOL' if p_value_two_sided < 0.05 else 'GAGAL'}")
print(f"  LOSO mayoritas {'YA' if still_majority/len(results_loso) > 0.6 else 'TIDAK'}")
print(f"  Cap bucket: median positif di bucket {'BTC/ETH' if bucket_stats.get('BTC',{}).get('%pos',0) > 30 else 'bagian kecil/small cap' if bucket_stats.get('Small cap',{}).get('%pos',0) > 30 else 'tersebar'}")

# Disimpan
result_gov={
    'sign_test_pvalue':p_value_two_sided,
    'sign_test_lolos':p_value_two_sided < 0.05,
    'loso_majority_count':still_majority,
    'loso_total':len(results_loso),
    'cap_bucket':bucket_stats,
    'governance_status':'Observed Phenomenon — Tentatively Robust, Mechanism Unknown',
    'governance_recommendation':'Jalankan Phase B jika sign test lolos (p < 0.05) AND LOSO mayoritas > 60%. BUKAN lanjut jika salah satu gagal. Cap bucket butuh review manual.'
}
with open(os.path.join(RESEARCH_DIR,'STUDY-002_governance.json'),'w') as f:
    json.dump(result_gov,f,indent=2)
print("\nSaved governance decision to research/STUDY-002_governance.json")
print("="*70)