import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import market_snapshot as market_snapshot_module  # noqa: E402
from market_snapshot import (  # noqa: E402
    SCHEMA_VERSION,
    ResilientProvider,
    build_snapshot,
    calculate_ma,
    calculate_window_metrics,
    determine_completeness,
    normalize_scalar,
    normalize_stock_code,
    redact_secrets,
    select_latest_complete_cache,
)


class FailingProvider:
    name = "akshare"

    def fetch_indices(self):
        raise RuntimeError("primary unavailable token=secret")


class FallbackProvider:
    name = "zhitu"

    def fetch_indices(self):
        return [{"code": "000001", "price": 3200.0}]

class FakeProvider:
    name = "fake-akshare"

    def health(self):
        return {"ok": True, "version": "test"}

    def fetch_indices(self):
        return [{"code": "000001", "name": "上证指数", "price": 3200.0}]

    def fetch_market_spot(self):
        return [
            {"code": "000001", "name": "平安银行", "pct_change": 1.0, "amount": 100.0},
            {"code": "000002", "name": "万科A", "pct_change": -1.0, "amount": 200.0},
            {"code": "000004", "name": "国华网安", "pct_change": 0.0, "amount": 50.0},
        ]

    def fetch_limit_pools(self, trade_date):
        return {
            "limit_up": [{"code": "000001", "consecutive_boards": 2}],
            "limit_down": [],
            "previous": [],
            "strong": [],
            "broken": [],
        }

    def fetch_boards(self, trade_date):
        history = [
            {"date": f"2026-06-{day:02d}", "close": 100 + day, "high": 101 + day, "amount": 1000 + day}
            for day in range(1, 23)
        ]
        return {
            "industries": [{"name": "小金属", "history": history, "constituents": []}],
            "concepts": [{"name": "培育钻石", "history": history, "constituents": []}],
        }

    def fetch_stock_details(self, symbols, trade_date):
        return []


class MarketSnapshotTests(unittest.TestCase):
    def test_normalize_scalar_converts_missing_markers_and_numpy_like_values(self):
        class NumericValue:
            def item(self):
                return 12.5

        self.assertIsNone(normalize_scalar("-"))
        self.assertIsNone(normalize_scalar("--"))
        self.assertIsNone(normalize_scalar(float("nan")))
        self.assertEqual(normalize_scalar(NumericValue()), 12.5)

    def test_normalize_stock_code_supports_common_formats(self):
        self.assertEqual(normalize_stock_code("sz000001"), "000001.SZ")
        self.assertEqual(normalize_stock_code("600000.SH"), "600000.SH")
        self.assertEqual(normalize_stock_code("688001"), "688001.SH")
        self.assertEqual(normalize_stock_code("300001"), "300001.SZ")
        self.assertEqual(normalize_stock_code("920001"), "920001.BJ")

    def test_calculate_ma_returns_ma5_and_ma10(self):
        records = [{"close": float(value)} for value in range(1, 11)]
        self.assertEqual(calculate_ma(records), {"ma5": 8.0, "ma10": 5.5})

    def test_calculate_window_metrics_uses_5_10_20_day_windows(self):
        records = [
            {"date": f"d{i}", "close": 100 + i, "high": 101 + i, "amount": 1000 + i}
            for i in range(21)
        ]
        metrics = calculate_window_metrics(records)
        self.assertAlmostEqual(metrics["return_5d"], (120 / 115 - 1) * 100, places=6)
        self.assertAlmostEqual(metrics["return_10d"], (120 / 110 - 1) * 100, places=6)
        self.assertAlmostEqual(metrics["return_20d"], 20.0, places=6)
        self.assertEqual(metrics["positive_days_20d"], 20)
        self.assertAlmostEqual(metrics["distance_from_20d_high"], (120 / 121 - 1) * 100, places=6)

    def test_redact_secrets_masks_token_query_and_environment_value(self):
        text = "https://api.example.test?q=1&token=secret-value ZHITU_API_TOKEN=secret-value"
        redacted = redact_secrets(text, secrets=["secret-value"])
        self.assertNotIn("secret-value", redacted)
        self.assertIn("token=***", redacted)
        self.assertIn("ZHITU_API_TOKEN=***", redacted)

    def test_post_close_before_1710_is_partial(self):
        result = determine_completeness(
            mode="post_close",
            now=datetime(2026, 6, 22, 16, 30),
            trade_date="2026-06-22",
            latest_history_date="2026-06-22",
            market_coverage=0.99,
            board_history_complete=True,
        )
        self.assertEqual(result["status"], "partial")
        self.assertIn("17:10", " ".join(result["reasons"]))

    def test_auction_before_0925_is_failed(self):
        result = determine_completeness(
            mode="auction",
            now=datetime(2026, 6, 23, 9, 20),
            trade_date="2026-06-22",
            latest_history_date="2026-06-22",
            market_coverage=0.99,
            board_history_complete=True,
        )
        self.assertEqual(result["status"], "failed")
        self.assertIn("9:25", " ".join(result["reasons"]))

    def test_missing_history_or_low_coverage_prevents_complete(self):
        result = determine_completeness(
            mode="post_close",
            now=datetime(2026, 6, 22, 18, 0),
            trade_date="2026-06-22",
            latest_history_date="2026-06-18",
            market_coverage=0.75,
            board_history_complete=False,
        )
        self.assertEqual(result["status"], "partial")
        reasons = " ".join(result["reasons"])
        self.assertIn("交易日", reasons)
        self.assertIn("覆盖率", reasons)
        self.assertIn("板块历史", reasons)

    def test_build_snapshot_outputs_contract_and_consistent_breadth(self):
        snapshot = build_snapshot(
            provider=FakeProvider(),
            mode="post_close",
            now=datetime(2026, 6, 22, 18, 0),
            trade_date="2026-06-22",
            symbols=[],
        )
        self.assertEqual(snapshot["meta"]["schema_version"], SCHEMA_VERSION)
        self.assertEqual(snapshot["meta"]["completeness"], "complete")
        self.assertEqual(snapshot["market"]["breadth"]["valid"], 3)
        self.assertEqual(snapshot["market"]["breadth"]["up"], 1)
        self.assertEqual(snapshot["market"]["breadth"]["down"], 1)
        self.assertEqual(snapshot["market"]["breadth"]["flat"], 1)
        self.assertEqual(snapshot["market"]["total_amount"], 350.0)
        self.assertEqual(snapshot["risk"]["status"], "not_checked")
        json.dumps(snapshot, ensure_ascii=False)

    def test_select_latest_complete_cache_ignores_partial_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            for date, status in (("2026-06-20", "complete"), ("2026-06-21", "partial")):
                payload = {"meta": {"trade_date": date, "completeness": status}}
                (cache_dir / f"{date}.json").write_text(json.dumps(payload), encoding="utf-8")

            selected = select_latest_complete_cache(cache_dir)
            self.assertEqual(selected["meta"]["trade_date"], "2026-06-20")

    def test_resilient_provider_uses_optional_fallback_and_records_warning(self):
        provider = ResilientProvider(FailingProvider(), FallbackProvider(), secrets=["secret"])
        rows = provider.fetch_indices()
        self.assertEqual(rows[0]["code"], "000001")
        self.assertEqual(provider.used_providers, ["akshare", "zhitu"])
        self.assertEqual(len(provider.warnings), 1)
        self.assertNotIn("secret", provider.warnings[0])
    def test_health_snapshot_initializes_warnings(self):
        class HealthyAKShareProvider:
            name = "akshare"

            def __init__(self, **kwargs):
                pass

            def health(self):
                return {"ok": True, "version": "1.18.64", "endpoint_ok": True}

        with patch.object(market_snapshot_module, "AKShareProvider", HealthyAKShareProvider):
            snapshot = market_snapshot_module._health_snapshot(datetime(2026, 6, 22, 18, 0))
        self.assertEqual(snapshot["meta"]["warnings"], [])
        self.assertEqual(snapshot["meta"]["completeness"], "complete")

if __name__ == "__main__":
    unittest.main()
