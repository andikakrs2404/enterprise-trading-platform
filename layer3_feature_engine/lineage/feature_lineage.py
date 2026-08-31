#!/usr/bin/env python3
"""
Layer 3 - Feature Lineage
Melacak dependensi antar feature (enterprise requirement).

Dengan lineage, sistem bisa menjawab:
"Feature X berubah → Feature Y terpengaruh → Strategy Z terpengaruh"

Contoh:
compression_components
    ├── atr_ratio → ATR14
    ├── bb_width → BB20
    └── volume_ratio → volume / MA20
"""
from typing import Dict, List, Any, Optional
from ..contracts.feature_metadata import ATOMIC_FEATURES, CONTEXT_FEATURES


class FeatureLineage:
    """
    Membangun dan menanyakan graph dependensi feature.
    """
    
    def __init__(self):
        self.graph: Dict[str, List[str]] = {}  # feature -> deps
        self._build_graph()
    
    def _build_graph(self):
        """Bangun graph dependensi dari registry metadata."""
        all_meta = {**ATOMIC_FEATURES, **CONTEXT_FEATURES}
        for name, meta in all_meta.items():
            deps = list(meta.dependencies) if meta.dependencies else []
            # Juga tambahkan source data sebagai dependensi dasar
            for s in meta.source:
                if s not in deps:
                    deps.append(s)
            self.graph[name] = deps
    
    def get_dependencies(self, feature_name: str) -> List[str]:
        """Dependensi langsung sebuah feature."""
        return self.graph.get(feature_name, [])
    
    def get_dependents(self, feature_name: str) -> List[str]:
        """
        Feature apa saja yang TERGANTUNG pada feature ini?
        (kebalikan dari dependensi)
        """
        dependents = []
        for feat, deps in self.graph.items():
            if feature_name in deps:
                dependents.append(feat)
        return dependents
    
    def trace_impact(self, changed_feature: str, max_depth: int = 5) -> Dict[str, Any]:
        """
        Lacak semua feature yang terpengaruh jika satu feature berubah.
        
        Args:
            changed_feature: feature yang berubah
            max_depth: kedalaman maksimum tracing
            
        Returns:
            Dict: {impacted: [list of feature], path: {feature: [dependents chain]}}
        """
        impacted = []
        visited = set()
        
        def dfs(node, depth):
            if depth > max_depth or node in visited:
                return
            visited.add(node)
            dependents = self.get_dependents(node)
            for dep in dependents:
                impacted.append(dep)
                dfs(dep, depth + 1)
        
        dfs(changed_feature, 0)
        
        return {
            "changed_feature": changed_feature,
            "impacted_feature_count": len(impacted),
            "impacted_features": impacted,
        }
    
    def get_upstream_sources(self, feature_name: str) -> List[str]:
        """
        Semua sumber data upstream dari sebuah feature (transitively).
        Menjawab: "Feature ini berasal dari data apa?"
        """
        sources = set()
        visited = set()
        
        def collect(node):
            if node in visited:
                return
            visited.add(node)
            deps = self.get_dependencies(node)
            for d in deps:
                # Jika d adalah data source (bukan feature), tandai
                if d in ("open", "high", "low", "close", "volume",
                         "open_interest", "funding_rate", "orderbook"):
                    sources.add(d)
                else:
                    collect(d)  # d adalah feature, rekursi
        
        collect(feature_name)
        return sorted(sources)


# Quick test
if __name__ == "__main__":
    print("=" * 60)
    print("FEATURE LINEAGE TEST")
    print("=" * 60)
    
    lin = FeatureLineage()
    
    print("\n1. Dependensi compression_components:")
    print(f"   {lin.get_dependencies('compression_components')}")
    
    print("\n2. Upstream sources of atr_ratio:")
    print(f"   {lin.get_upstream_sources('atr_ratio')}")
    
    print("\n3. Siapa dependents dari atr_ratio (siapa yang terpengaruh jika atr_ratio berubah):")
    print(f"   {lin.get_dependents('atr_ratio')}")
    
    print("\n4. Trace impact jika adx berubah:")
    impact = lin.trace_impact('adx')
    print(f"   {impact['impacted_feature_count']} feature terpengaruh: {impact['impacted_features']}")
    
    print("\n" + "=" * 60)
    print("✓ Feature Lineage Operational")
    print("=" * 60)
