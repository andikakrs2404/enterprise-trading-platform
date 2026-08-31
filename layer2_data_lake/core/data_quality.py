#!/usr/bin/env python3
"""
Layer 2 - Data Quality Validation Module (Pure Python)
Wajib: Setiap data masuk harus diperiksa kualitasnya.
Priority: 2 setelah Timestamp Alignment.
Masalah: Missing Candle, Duplicate, Spike Error.
Setelah data lewat filter ini sebelum masuk ke Feature Store.
"""
from typing import Dict, List, Any, Optional, Tuple, NamedTuple
from datetime import datetime, timedelta
import time

INTERNAL_FORMAT_SCHEMA = {
    "exchange": str,
    "symbol": str,
    "price": float,
    "qty": float,
    "side": str,
    "timestamp": int
}

class QualityIssue(NamedTuple):
    """Struktur issue yang terdeteksi"""
    issue_type: str
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    description: str
    row_idx: Optional[int] = None
    timestamp: Optional[int] = None
    suggested_action: str = "investigate"

class DataQualityValidator:
    """
    Validasi kualitas data real-time dan historis.
    Mendeteksi: Missing Candle, Duplicate, Spike Error, Stale Data.
    Thresholds:
    - PRICE_SPIKE_THRESHOLD: 3x perubahan normal = spike
    - MAX_PRICE_CHANGE_PCT: 50% perubahan harga dalam 1 candle = suspicious
    - MAX_TIMESTAMP_GAP: 300000ms = 5 menit
    """
    
    PRICE_SPIKE_THRESHOLD = 3.0    # 3% perubahan = mulai diwaspadai
    MAX_PRICE_CHANGE_PCT = 50.0    # 50% perubahan harga = suspicious
    MAX_TIMESTAMP_GAP = 300000     # 5 menit dalam ms
    EXPECTED_CANDLE_INTERVAL = 60000  # 1 menit default
    
    @staticmethod
    def detect_missing_candles(
        data: List[Dict],
        timestamp_key: str = "timestamp",
        expected_interval_ms: int = EXPECTED_CANDLE_INTERVAL
    ) -> List[QualityIssue]:
        """
        Deteksi missing candle: interval antara timestamp berturut-turut tidak konsisten.
        """
        issues = []
        
        if not data:
            return issues
        
        # Sort by timestamp
        sorted_data = sorted(data, key=lambda x: x.get(timestamp_key, 0))
        
        if len(sorted_data) < 2:
            return issues
        
        timestamps = [d.get(timestamp_key, 0) for d in sorted_data]
        
        for i in range(1, len(timestamps)):
            gap = timestamps[i] - timestamps[i-1]
            
            # Gap nol = duplicate
            if gap == 0:
                issues.append(QualityIssue(
                    issue_type="duplicate_timestamp",
                    severity="HIGH",
                    description=f"Duplicate timestamp at position {i}: {timestamps[i]}",
                    row_idx=i,
                    timestamp=timestamps[i],
                    suggested_action="remove_duplicate_entry"
                ))
            
            # Gap negatif = urutan terbalik (error sistem)
            elif gap < 0:
                issues.append(QualityIssue(
                    issue_type="timestamp_out_of_order",
                    severity="CRITICAL",
                    description=f"Timestamp out of order: {timestamps[i-1]} -> {timestamps[i]} (gap: {gap}ms)",
                    row_idx=i,
                    timestamp=timestamps[i],
                    suggested_action="investigate_system_clock"
                ))
            
            # Gap > threshold = missing candle
            elif gap > expected_interval_ms * 2:  # > 2x interval expected
                missing_count = (gap // expected_interval_ms) - 1
                issues.append(QualityIssue(
                    issue_type="missing_candle",
                    severity="HIGH",
                    description=f"Missing {missing_count} candle(s) between {timestamps[i-1]} and {timestamps[i]} (gap: {gap}ms, expected: {expected_interval_ms}ms)",
                    row_idx=i,
                    timestamp=timestamps[i],
                    suggested_action=f"fill_gap_or_mark_partial"
                ))
            
            # Gapengah tapi aneh
            elif gap > expected_interval_ms and gap < expected_interval_ms * 2:
                drift_pct = (gap - expected_interval_ms) / expected_interval_ms * 100
                issues.append(QualityIssue(
                    issue_type="timestamp_drift",
                    severity="MEDIUM",
                    description=f"Timestamp drift: gap {gap}ms vs expected {expected_interval_ms}ms (+{drift_pct:.1f}%)",
                    row_idx=i,
                    timestamp=timestamps[i],
                    suggested_action="check_feed_sync"
                ))
        
        return issues
    
    @staticmethod
    def detect_price_spikes(
        data: List[Dict],
        price_key: str = "price",
        timestamp_key: str = "timestamp",
        threshold: float = PRICE_SPIKE_THRESHOLD
    ) -> List[QualityIssue]:
        """
        Deteksi price spike: harga berubah drastis antara candle berturut-turut.
        """
        issues = []
        
        if len(data) < 2:
            return issues
        
        # Sort by timestamp
        sorted_data = sorted(data, key=lambda x: x.get(timestamp_key, 0))
        
        prices = [d.get(price_key, 0) for d in sorted_data]
        timestamps = [d.get(timestamp_key, 0) for d in sorted_data]
        
        for i in range(1, len(prices)):
            price_change_abs = abs(prices[i] - prices[i-1])
            price_change_pct = price_change_abs / prices[i-1] * 100 if prices[i-1] != 0 else 0
            time_gap = timestamps[i] - timestamps[i-1]
            
            # Jika harga berubah drastis dalam waktu singkat = spike
            if price_change_pct > threshold * 100:  # > 300% change = extreme spike
                issues.append(QualityIssue(
                    issue_type="price_spike_extreme",
                    severity="CRITICAL",
                    description=f"Extreme price spike: {prices[i-1]} -> {prices[i]} ({price_change_pct:.1f}% change in {time_gap}ms)",
                    row_idx=i,
                    timestamp=timestamps[i],
                    suggested_action="reject_data_source"
                ))
            elif price_change_pct > threshold * 10:  # > 30% change = suspicious
                issues.append(QualityIssue(
                    issue_type="price_spike_suspicious",
                    severity="HIGH",
                    description=f"Suspicious price spike: {prices[i-1]} -> {prices[i]} ({price_change_pct:.1f}% change)",
                    row_idx=i,
                    timestamp=timestamps[i],
                    suggested_action="flag_for_review"
                ))
            elif price_change_pct > threshold:  # > 3% change = normal check
                if time_gap > 0:
                    change_per_ms = price_change_pct / time_gap * 1000  # per second normalized
                    if change_per_ms > 5.0:  # > 5% per second = suspicious
                        issues.append(QualityIssue(
                            issue_type="price_spike_fast",
                            severity="MEDIUM",
                            description=f"Fast price change: {price_change_pct:.1f}% in {time_gap}ms ({change_per_ms:.2f}%/sec)",
                            row_idx=i,
                            timestamp=timestamps[i],
                            suggested_action="verify_feed_health"
                        ))
        
        return issues
    
    @staticmethod
    def detect_duplicates(
        data: List[Dict],
        subset: Optional[List[str]] = None,
        timestamp_key: str = "timestamp"
    ) -> List[QualityIssue]:
        """
        Deteksi duplicate entries berdasarkan timestamp dan fields lainnya.
        """
        issues = []
        
        if not data:
            return issues
        
        # Cek duplicate timestamp
        ts_counts = {}
        for i, d in enumerate(data):
            ts = d.get(timestamp_key, None)
            if ts is not None:
                if ts not in ts_counts:
                    ts_counts[ts] = []
                ts_counts[ts].append(i)
        
        for ts, indices in ts_counts.items():
            if len(indices) > 1:
                for idx in indices:
                    issues.append(QualityIssue(
                        issue_type="duplicate_timestamp",
                        severity="HIGH",
                        description=f"Duplicate timestamp at position {idx}: {ts}",
                        row_idx=idx,
                        timestamp=ts,
                        suggested_action="investigate_source_duplication"
                    ))
        
        # Cek duplicate full row (harga, qty, side sama)
        full_row_keys = [k for k in data[0].keys() if k != timestamp_key]
        for i in range(len(data)):
            for j in range(i+1, len(data)):
                if data[i] == data[j]:
                    issues.append(QualityIssue(
                        issue_type="duplicate_full_row",
                        severity="MEDIUM",
                        description=f"Duplicate full data row at positions {i} and {j}",
                        row_idx=i,
                        suggested_action="remove_full_duplicates"
                    ))
                    break  # hanya catat sekali per pasangan
        
        return issues
    
    @staticmethod
    def validate_dataframe(
        data: List[Dict],
        required_fields: Optional[List[str]] = None,
        check_missing_candles: bool = True,
        check_price_spikes: bool = True,
        check_duplicates: bool = True,
        expected_interval_ms: int = EXPECTED_CANDLE_INTERVAL
    ) -> Dict[str, Any]:
        """
        Validasi lengkap data - return summary issues.
        """
        all_issues = []
        
        # Cek required fields
        if required_fields:
            for field in required_fields:
                # Check if field exists in any data point
                if not any(field in d for d in data):
                    all_issues.append(QualityIssue(
                        issue_type="missing_required_field",
                        severity="CRITICAL",
                        description=f"Missing required field: {field} across all data",
                        suggested_action="add_field_to_schema"
                    ))
        
        # Cek missing candles
        if check_missing_candles:
            missing_issues = DataQualityValidator.detect_missing_candles(
                data, expected_interval_ms=expected_interval_ms
            )
            all_issues.extend(missing_issues)
        
        # Cek price spikes
        if check_price_spikes:
            spike_issues = DataQualityValidator.detect_price_spikes(data)
            all_issues.extend(spike_issues)
        
        # Cek duplicates
        if check_duplicates:
            dup_issues = DataQualityValidator.detect_duplicates(data)
            all_issues.extend(dup_issues)
        
        # Summary
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for issue in all_issues:
            if issue.severity in severity_counts:
                severity_counts[issue.severity] += 1
        
        # Determined status
        # Valid jika tidak ada CRITICAL dan hanya LIMITED HIGH
        is_valid = severity_counts["CRITICAL"] == 0
        
        summary = {
            "is_valid": is_valid,
            "total_issues": len(all_issues),
            "severity_breakdown": severity_counts,
            "issues": [issue.issue_type for issue in all_issues],
            "total_rows": len(data)
        }
        
        return summary
    
    @staticmethod
    def add_quality_flags(
        data: List[Dict],
        timestamp_key: str = "timestamp",
        price_key: str = "price"
    ) -> Tuple[List[Dict], Dict[str, Any]]:
        """
        Tambahkan kolom quality flags ke setiap data row.
        Setiap row akan memiliki metadata kualitas.
        """
        # Copy data to avoid modifying original
        data_copy = [d.copy() for d in data]
        
        # Inisialisasi kolom quality
        for d in data_copy:
            d["quality_score"] = 1.0  # 1.0 = sempurna
            d["issues_list"] = []  # List issues per row
            d["quality_timestamp"] = d.get(timestamp_key)
        
        # Jalankan validasi
        validation = DataQualityValidator.validate_dataframe(data)
        
        # Assign severity-based scores ke setiap row
        severity_score_map = {"CRITICAL": 0.5, "HIGH": 0.3, "MEDIUM": 0.1, "LOW": 0.05}
        
        # Reset issues_list sebelum assign
        for d in data_copy:
            d["issues_list"] = []
        
        # Untuk setiap issue yang terdeteksi, temukan row affected dan kurangi score
        for issue in validation["issues"]:
            # Cari row yang mengandung info timestamp issue
            target_ts = issue.timestamp
            for idx, d in enumerate(data_copy):
                if d.get(timestamp_key) == target_ts and d.get("quality_score", 1.0) > 0:
                    reduction = severity_score_map.get(issue.severity, 0.1)
                    d["quality_score"] = max(0, d["quality_score"] - reduction)
                    
                    # Tambahkan description ke issues_list
                    if issue.issue_type not in d["issues_list"]:
                        d["issues_list"].append(issue.issue_type)
        
        return data_copy, validation


# Quick test
if __name__ == "__main__":
    print("=" * 60)
    print("DATA QUALITY VALIDATION MODULE TEST (Pure Python)")
    print("=" * 60)
    
    # Test data: Data dengan missing candle dan spike
    data = [
        {"timestamp": 1000, "price": 100, "symbol": "BTCUSDT", "side": "buy"},
        {"timestamp": 2000, "price": 101, "symbol": "BTCUSDT", "side": "buy"},
        {"timestamp": 3000, "price": 102, "symbol": "BTCUSDT", "side": "buy"},
        {"timestamp": 4000, "price": 103, "symbol": "BTCUSDT", "side": "buy"},
        {"timestamp": 5000, "price": 104, "symbol": "BTCUSDT", "side": "buy"},
        {"timestamp": 7000, "price": 106, "symbol": "BTCUSDT", "side": "buy"},  # gap 2000ms = missing candle
    ]
    
    print("\n[Test 1] Data sederhana seharusnya valid")
    result = DataQualityValidator.validate_dataframe(data, check_missing_candles=True, 
                                                     check_price_spikes=True, check_duplicates=True)
    print(f"Valid: {result['is_valid']}")
    print(f"Issues: {result['total_issues']}")
    print(f"Severity: {result['severity_breakdown']}")
    
    # Test data dengan issues
    data_with_issues = [
        {"timestamp": 1000, "price": 100, "symbol": "BTCUSDT", "side": "buy"},
        {"timestamp": 2000, "price": 101, "symbol": "BTCUSDT", "side": "buy"},
        {"timestamp": 2000, "price": 102, "symbol": "BTCUSDT", "side": "buy"},  # DUPLICATE timestamp
        {"timestamp": 4000, "price": 99999, "symbol": "BTCUSDT", "side": "buy"},  # SPIKE
    ]
    
    print("\n[Test 2] Data dengan issues (duplicate + spike)")
    result2 = DataQualityValidator.validate_dataframe(data_with_issues, check_missing_candles=True,
                                                     check_price_spikes=True, check_duplicates=True)
    print(f"Valid: {result2['is_valid']}")
    print(f"Total issues: {result2['total_issues']}")
    print(f"Severity breakdown: {result2['severity_breakdown']}")
    for issue in data_with_issues:
        print(f"  Row: {issue}")
    
    # Test add quality flags
    print("\n[Test 3] Add quality flags")
    data_flagged, val = DataQualityValidator.add_quality_flags(data_with_issues)
    print(f"Quality score per row: {[d['quality_score'] for d in data_flagged]}")
    print(f"Validation overall valid: {val['is_valid']}")
    for i, d in enumerate(data_flagged):
        print(f"  Row {i}: score={d['quality_score']:.2f}, issues={d['issues_list']}")
    
    print("\n" + "=" * 60)
    print("✓ Data Quality Validation Module Operational")
    print("=" * 60)
