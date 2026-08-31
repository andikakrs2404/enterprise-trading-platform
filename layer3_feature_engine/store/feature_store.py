#!/usr/bin/env python3
"""
Layer 3 - Feature Store
Sumber kebenaran untuk semua feature yang dihitung.

Pipeline:
Raw Data → Feature Calculation → Validation → Storage → Versioning → Serving

Ini yang membedakan retail (hitung indikator on-the-fly) 
dengan enterprise (feature konsisten reusable).

Feature yang sama dipakai oleh:
- Backtest
- Research
- ML Training
- Live Trading
Sehingga hasil konsisten (tidak ada live vs backtest mismatch).
"""
from typing import Dict, List, Any, Optional
import json
import os
import time
import datetime


class FeatureStore:
    """
    Feature Store dengan pipeline lengkap.
    Menyimpan feature dengan schema version, quality score, dan auditability.
    """
    
    # Schema version - increments saat format berubah
    SCHEMA_VERSION = "1.0.0"
    
    def __init__(self, storage_dir: Optional[str] = None, config: Optional[Dict] = None):
        """Inisialisasi Feature Store dengan direktori storage."""
        self.config = config or {}
        # Dari config (bukan hardcoded - fix CodeRabbit)
        self.storage_dir = storage_dir or self.config.get("storage_dir", 
                            os.path.join(os.path.dirname(os.path.abspath(__file__)), "store", "storage"))
        os.makedirs(self.storage_dir, exist_ok=True)
        
        self._feature_meta = {}  # feature name -> metadata
        self._version_info = {}
        self.dataset_version = self.config.get("initial_version", "v1.0.0")
    
    def _get_feature_file(self, symbol: str, dataset_version: str = None) -> str:
        """Path file untuk menyimpan feature data."""
        version = dataset_version or self.dataset_version
        safe_symbol = symbol.replace("/", "").replace("-", "")
        return os.path.join(self.storage_dir, f"{safe_symbol}_{version}.jsonl")
    
    # --- PIPELINE STEP 1: Store / Save ---
    def save_features(self, symbol: str, feature_rows: List[Dict], 
                      source: str = "feature_engine", 
                      quality_scores: Optional[List[float]] = None) -> Dict[str, Any]:
        """
        Simpan feature rows ke storage (hot storage, JSONL).
        
        Args:
            symbol: Simbol pasar (BTCUSDT)
            feature_rows: List dict feature per bar
            source: Sumber feature (untuk audit)
            quality_scores: Skor kualitas per bar (jika ada)
            
        Returns:
            Dict info penyimpanan
        """
        file_path = self._get_feature_file(symbol)
        write_mode = "a" if os.path.exists(file_path) else "w"
        
        rows_written = 0
        with open(file_path, write_mode) as f:
            for idx, row in enumerate(feature_rows):
                # Tambah metadata untuk audit
                enriched_row = {
                    "schema_version": self.SCHEMA_VERSION,
                    "dataset_version": self.dataset_version,
                    "source": source,
                    "saved_at": datetime.datetime.utcnow().isoformat(),
                    "quality_score": quality_scores[idx] if quality_scores and idx < len(quality_scores) else 1.0,
                    **row,  # feature values
                }
                f.write(json.dumps(enriched_row) + "\n")
                rows_written += 1
        
        return {
            "symbol": symbol,
            "rows_written": rows_written,
            "file": file_path,
            "dataset_version": self.dataset_version,
            "schema_version": self.SCHEMA_VERSION,
            "status": "saved"
        }
    
    # --- PIPELINE STEP 2: Read ---
    def load_features(self, symbol: str, dataset_version: str = None,
                      limit: Optional[int] = None) -> List[Dict]:
        """
        Load feature rows dari storage.
        Memastikan backtest dan live trading pakai data yang SAMA.
        """
        file_path = self._get_feature_file(symbol, dataset_version)
        if not os.path.exists(file_path):
            return []
        
        rows = []
        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
                    if limit and len(rows) >= limit:
                        break
        return rows
    
    # --- PIPELINE STEP 3: Versioning ---
    def snapshot_version(self, symbol: str = "ALL", description: str = "") -> Dict[str, Any]:
        """
        Buat snapshot version dari data saat ini.
        Ini memastikan reproducibility: backtest harus tahu dataset mana yang dipakai.
        
        Example: dataset_version: "v2.4.1"
        """
        # Parse current version and increment
        v_parts = self.dataset_version.lstrip("v").split(".")
        if len(v_parts) == 3:
            major, minor, patch = int(v_parts[0]), int(v_parts[1]), int(v_parts[2])
            new_patch = patch + 1
            new_version = f"v{major}.{minor}.{new_patch}"
        else:
            new_version = self.dataset_version + ".1"
        
        snapshot = {
            "version": new_version,
            "previous_version": self.dataset_version,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "symbol": symbol,
            "description": description,
            "schema_version": self.SCHEMA_VERSION,
            "features_included": self.list_features(symbol),
        }
        
        # Tandai dataset version baru
        self.dataset_version = new_version
        self._version_info[new_version] = snapshot
        
        # Simpan version info
        version_file = os.path.join(self.storage_dir, "VERSIONS.json")
        existing = {}
        if os.path.exists(version_file):
            with open(version_file) as f:
                existing = json.load(f)
        existing[new_version] = snapshot
        with open(version_file, "w") as f:
            json.dump(existing, f, indent=2)
        
        return snapshot
    
    def get_versions(self) -> Dict[str, Any]:
        """Dapatkan semua versi dataset yang ada."""
        version_file = os.path.join(self.storage_dir, "VERSIONS.json")
        if os.path.exists(version_file):
            with open(version_file) as f:
                return json.load(f)
        return {}
    
    # --- PIPELINE STEP 4: Validation ---
    def validate_features(self, rows: List[Dict], 
                          required_features: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Validasi feature data sebelum dipakai model/strategi.
        Check:
        - Schema version konsisten
        - Required features ada
        - Tidak ada NaN/inf
        - Quality score memenuhi threshold
        """
        if not rows:
            return {"is_valid": False, "reason": "empty_data"}
        
        issues = []
        required = required_features or self.config.get("critical_features", [])
        
        # Schema check
        versions = set(r.get("schema_version", "?") for r in rows)
        if len(versions) > 1:
            issues.append(f"Inconsistent schema_version: {versions}")
        
        # Required features check
        for rf in required:
            missing = [r for r in rows if rf not in r]
            if len(missing) == len(rows):
                issues.append(f"Required feature '{rf}' missing from ALL rows")
        
        # NaN / inf check
        for i, r in enumerate(rows[:100]):  # sample max 100
            for k, v in r.items():
                if isinstance(v, float):
                    if v != v:  # NaN
                        issues.append(f"Row {i} feature '{k}': NaN")
                    elif v == float('inf') or v == float('-inf'):
                        issues.append(f"Row {i} feature '{k}': infinite")
        
        # Quality score check
        min_q = self.config.get("min_quality_score", 0.85)
        low_quality = [r for r in rows if r.get("quality_score", 1.0) < min_q]
        if len(low_quality) > len(rows) * 0.05:  # >5% low quality
            issues.append(f"{len(low_quality)}/{len(rows)} rows di bawah quality threshold {min_q}")
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "total_rows": len(rows),
            "schema_version": rows[0].get("schema_version", "?") if rows else "?",
            "dataset_version": rows[0].get("dataset_version", "?") if rows else "?",
        }
    
    # --- PIPELINE STEP 5: Serving ---
    def get_feature_batch(self, symbol: str, features: List[str], 
                          dataset_version: str = None, limit: int = 1000) -> List[Dict]:
        """
        Serve feature untuk consumption (strategi, model, backtest).
        Memastikan konsistensi: selalu pakai versi dataset yang ditentukan.
        """
        rows = self.load_features(symbol, dataset_version, limit=limit)
        if not rows:
            return []
        
        # Filter hanya feature yang diminta + identitas
        ident = ["timestamp", "symbol", "schema_version", "dataset_version", "quality_score"]
        filtered = []
        for r in rows:
            row = {k: r.get(k) for k in ident if k in r}
            for f in features:
                if f in r:
                    row[f] = r[f]
            filtered.append(row)
        
        return filtered
    
    def list_features(self, symbol: str = None) -> List[str]:
        """List semua feature yang tersimpan untuk symbol tertentu."""
        if symbol is None:
            # Scan semua file
            all_features = set()
            for fname in os.listdir(self.storage_dir):
                if fname.endswith(".jsonl"):
                    path = os.path.join(self.storage_dir, fname)
                    try:
                        with open(path) as f:
                            first_line = f.readline()
                            if first_line:
                                row = json.loads(first_line)
                                all_features.update(k for k in row if k not in 
                                    ["schema_version", "dataset_version", "source", 
                                     "saved_at", "quality_score", "timestamp", "symbol"])
                    except:
                        pass
            return sorted(all_features)
        else:
            rows = self.load_features(symbol, limit=1)
            if rows:
                return sorted(k for k in rows[0] if k not in 
                    ["schema_version", "dataset_version", "source", "saved_at",
                     "quality_score", "timestamp", "symbol"])
            return []
    
    def get_audit_info(self, symbol: str, dataset_version: str = None) -> List[Dict]:
        """
        Audit trail: siapa/kapan/apa yang disimpan.
        Penting untuk auditability (yang paling sering menghancurkan quant system).
        """
        rows = self.load_features(symbol, dataset_version)
        audit = []
        for r in rows:
            audit.append({
                "symbol": r.get("symbol", symbol),
                "timestamp": r.get("timestamp"),
                "saved_at": r.get("saved_at"),
                "source": r.get("source"),
                "schema_version": r.get("schema_version"),
                "dataset_version": r.get("dataset_version"),
                "quality_score": r.get("quality_score"),
            })
        return audit


# Quick test
if __name__ == "__main__":
    print("=" * 60)
    print("FEATURE STORE TEST — Pipeline Raw→Validation→Versioning→Serving")
    print("=" * 60)
    
    # Inisialisasi store
    store_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "store", "storage", "test")
    store = FeatureStore(storage_dir=store_dir)
    
    # Simpan sample features
    sample_rows = [
        {"timestamp": 1000, "symbol": "BTCUSDT", "atr": 5.0, "atr_ratio": 0.55, "bb_width": 0.02, 
         "volume_ratio": 0.6, "compression_score": 0.85, "regime": "COMPRESSION"},
        {"timestamp": 2000, "symbol": "BTCUSDT", "atr": 5.5, "atr_ratio": 0.5, "bb_width": 0.019, 
         "volume_ratio": 0.5, "compression_score": 0.9, "regime": "COMPRESSION"},
        {"timestamp": 3000, "symbol": "BTCUSDT", "atr": 8.0, "atr_ratio": 1.8, "bb_width": 0.09, 
         "volume_ratio": 3.5, "compression_score": 0.1, "regime": "VOLATILITY_EXPANSION"},
    ]
    
    # Step 1: Save
    print("\n[1] Save features")
    save_info = store.save_features("BTCUSDT", sample_rows, source="test")
    print(f"  Rows saved: {save_info['rows_written']}, file: {save_info['file']}")
    
    # Step 2: Version
    print("\n[2] Snapshot version")
    snapshot = store.snapshot_version(symbol="BTCUSDT", description="Initial compression test")
    print(f"  New version: {snapshot['version']}, previous: {snapshot['previous_version']}")
    
    # Step 3: Load
    print("\n[3] Load features")
    loaded = store.load_features("BTCUSDT")
    print(f"  Loaded {len(loaded)} rows, dataset_version={loaded[0]['dataset_version'] if loaded else 'N/A'}")
    
    # Step 4: Validate
    print("\n[4] Validate features")
    validation = store.validate_features(loaded, required_features=["atr", "atr_ratio", "bb_width"])
    print(f"  Valid: {validation['is_valid']}, issues: {validation['issues']}")
    
    # Step 5: Serve
    print("\n[5] Serve feature batch")
    served = store.get_feature_batch("BTCUSDT", ["atr_ratio", "bb_width", "compression_score"])
    print(f"  Served {len(served)} rows")
    for r in served[:2]:
        print(f"    {r}")
    
    # Step 6: Audit
    print("\n[6] Audit trail")
    audit = store.get_audit_info("BTCUSDT")
    print(f"  {len(audit)} audit entries, source={audit[0]['source'] if audit else 'N/A'}")
    
    print("\n" + "=" * 60)
    print("✓ Feature Store Operational — Full pipeline")
    print("=" * 60)
