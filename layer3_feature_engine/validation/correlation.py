#!/usr/bin/env python3
"""
Layer 3 - Feature Dependency & Correlation Analysis (P1)

Anda benar: 7 domain berbeda ≠ otomatis orthogonal.
ATR Ratio, Realized Vol, BB Width semuanya di Volatility → sangat berkorelasi.

Tool ini menghitung korelasi antar feature secara nyata,
sehingga kita TAHU berapa banyak "informasi independen" yang kita punya.

Output:
- Correlation matrix antar feature
- Feature pairs dengan korelasi tinggi (>0.85) → redundant
- eigein insight: berapa feature yang benar-benar independen
"""
from typing import List, Dict, Any, Optional
import math


class FeatureCorrelationAnalyzer:
    """
    Analisis korelasi Pearson antar feature.
    Membantu memilih feature yang orthogonal (tidak redundan).
    """
    
    def __init__(self, correlation_threshold: float = 0.85):
        self.threshold = correlation_threshold
    
    def compute_correlation_matrix(self, rows: List[Dict], 
                                   features: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Hitung korelasi Pearson antar feature.
        
        Args:
            rows: List feature rows
            features: List nama feature (default: semua numeric)
            
        Returns:
            Dict: {matrix: {feat1: {feat2: corr}}, high_pairs: [...], insights: [...]}
        """
        if not rows:
            return {"matrix": {}, "high_pairs": [], "insights": []}
        
        # Pilih feature numeric yang tersedia
        if features is None:
            features = []
            for k in rows[0]:
                if k not in ("timestamp", "symbol", "saved_at", "source",
                             "quality_score", "schema_version", "dataset_version",
                             "timeframe", "feature_status"):
                    if isinstance(rows[0][k], (int, float)):
                        features.append(k)
        features = [f for f in features if isinstance(rows[0].get(f), (int, float))]
        
        # Ekstrak series per feature
        series = {}
        for f in features:
            series[f] = [r.get(f, float('nan')) for r in rows]
        
        # Hitung korelasi pairwise
        matrix = {f: {} for f in features}
        high_pairs = []
        
        for i in range(len(features)):
            for j in range(i+1, len(features)):
                f1, f2 = features[i], features[j]
                corr = self._pearson(series[f1], series[f2])
                if corr is not None:
                    matrix[f1][f2] = round(corr, 4)
                    matrix[f2][f1] = round(corr, 4)
                    if abs(corr) > self.threshold:
                        high_pairs.append({
                            "feature_a": f1,
                            "feature_b": f2,
                            "correlation": round(corr, 4),
                            "redundant": True,
                        })
            matrix[f1][f1] = 1.0
        
        # Insights
        insights = []
        if high_pairs:
            insight = (f"⚠️ {len(high_pairs)} pasangan feature berkorelasi tinggi "
                       f"(>{self.threshold:.2f}): informasi REDUNDAN. ")
            pairs_str = ", ".join(f"{p['feature_a']}~{p['feature_b']}({p['correlation']:.2f})" 
                                   for p in high_pairs[:5])
            insights.append(insight + pairs_str)
        else:
            insights.append(f"✅ Tidak ada pasangan feature dengan korelasi > {self.threshold:.2f}. "
                            f"Feature reasonably orthogonal.")
        
        return {
            "matrix": matrix,
            "high_pairs": high_pairs,
            "insights": insights,
            "n_features": len(features),
            "n_redundant_pairs": len(high_pairs),
        }
    
    def _pearson(self, x: List[float], y: List[float]) -> Optional[float]:
        """Pearson correlation coefficient."""
        pairs = [(a, b) for a, b in zip(x, y) 
                 if isinstance(a, (int, float)) and isinstance(b, (int, float))
                 and a == a and b == b]  # filter non-nan
        n = len(pairs)
        if n < 3:
            return None
        x_vals = [p[0] for p in pairs]
        y_vals = [p[1] for p in pairs]
        x_mean = sum(x_vals) / n
        y_mean = sum(y_vals) / n
        num = sum((xv - x_mean) * (yv - y_mean) for xv, yv in pairs)
        den_x = math.sqrt(sum((xv - x_mean)**2 for xv in x_vals))
        den_y = math.sqrt(sum((yv - y_mean)**2 for yv in y_vals))
        if den_x == 0 or den_y == 0:
            return None
        return num / (den_x * den_y)


# Quick test
if __name__ == "__main__":
    import random
    random.seed(12)
    
    print("=" * 60)
    print("FEATURE CORRELATION ANALYSIS - Orthogonality Test")
    print("=" * 60)
    
    # Generate data: 3 feature sebenarnya berkorelasi (volatility family)
    # dan 2 feature independen (price_return, volume_ratio)
    n = 200
    rows = []
    base_vol = [random.random() for _ in range(n)]
    for i in range(n):
        # Volatility family: atr_ratio, realized_vol, bb_width — SALING BERKORELASI
        common_factor = base_vol[i]
        atr_ratio = 0.5 + common_factor * 0.4 + random.uniform(-0.03, 0.03)
        realized_vol = 0.01 + common_factor * 0.02 + random.uniform(-0.002, 0.002)
        bb_width = 0.02 + common_factor * 0.03 + random.uniform(-0.002, 0.002)
        # Independen: ret_1 (random walk), volume_ratio
        ret_1 = random.uniform(-0.02, 0.02)
        volume_ratio = random.uniform(0.5, 1.5)
        
        rows.append({
            "timestamp": i,
            "atr_ratio": atr_ratio,
            "realized_vol": realized_vol,
            "bb_width": bb_width,
            "ret_1": ret_1,
            "volume_ratio": volume_ratio,
        })
    
    analyzer = FeatureCorrelationAnalyzer(correlation_threshold=0.7)
    result = analyzer.compute_correlation_matrix(rows)
    
    print(f"\n{n} bar, {result['n_features']} feature, {result['n_redundant_pairs']} pasangan redundant")
    
    print("\nCorrelation matrix (subset):")
    feats = ["atr_ratio", "realized_vol", "bb_width", "ret_1", "volume_ratio"]
    print(f"{'':>14}", end="")
    for f in feats:
        print(f"{f[:8]:>10}", end="")
    print()
    for f1 in feats:
        print(f"{f1[:14]:>14}", end="")
        for f2 in feats:
            c = result['matrix'].get(f1, {}).get(f2)
            print(f"{c if c is not None else ' ':>10}", end="")
        print()
    
    print("\nInsights:")
    for ins in result['insights']:
        print(f"  {ins}")
    
    print("\n" + "=" * 60)
    print("✓ Correlation Analysis Operational — buktikan orthogonality")
    print("=" * 60)
