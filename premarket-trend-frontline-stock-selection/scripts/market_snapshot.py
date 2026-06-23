#!/usr/bin/env python3
"""Collect deterministic A-share market facts for the premarket skill."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, time as clock_time, timedelta
from pathlib import Path
from typing import Any, Iterable, Protocol


SCHEMA_VERSION = "1.0"
MIN_MARKET_COVERAGE = 0.90
POST_CLOSE_READY_TIME = clock_time(17, 10)
AUCTION_READY_TIME = clock_time(9, 25)
DEFAULT_CACHE_DIR = Path(tempfile.gettempdir()) / "codex-premarket-cache"
REQUIRED_RISK_SOURCES = ["巨潮资讯", "交易所公告"]


def normalize_scalar(value: Any) -> Any:
    """Convert dataframe scalars and common missing markers into JSON values."""
    if value is None:
        return None
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        try:
            value = value.item()
        except (TypeError, ValueError):
            pass
    if isinstance(value, str):
        value = value.strip()
        if value in {"", "-", "--", "None", "null", "NaN", "nan"}:
            return None
        return value
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    return value


def normalize_stock_code(value: str) -> str:
    """Normalize six-digit, prefixed, and suffixed stock codes."""
    raw = str(value).strip().upper()
    suffix_match = re.fullmatch(r"(\d{6})\.(SH|SZ|BJ)", raw)
    if suffix_match:
        return raw
    prefix_match = re.fullmatch(r"(SH|SZ|BJ)(\d{6})", raw)
    if prefix_match:
        return f"{prefix_match.group(2)}.{prefix_match.group(1)}"
    digits = re.sub(r"\D", "", raw)
    if len(digits) != 6:
        raise ValueError(f"无法识别股票代码: {value}")
    if digits.startswith(("4", "8", "92")):
        market = "BJ"
    elif digits.startswith(("5", "6", "9")):
        market = "SH"
    else:
        market = "SZ"
    return f"{digits}.{market}"


def redact_secrets(text: Any, secrets: Iterable[str] | None = None) -> str:
    """Mask query-string tokens, environment assignments, and known secret values."""
    result = str(text)
    result = re.sub(r"(?i)([?&]token=)[^&\s]+", r"\1***", result)
    result = re.sub(r"(?i)(ZHITU_API_TOKEN=)[^\s]+", r"\1***", result)
    for secret in secrets or []:
        if secret:
            result = result.replace(secret, "***")
    return result


def _numeric(value: Any) -> float | None:
    value = normalize_scalar(value)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def calculate_ma(records: list[dict[str, Any]]) -> dict[str, float | None]:
    closes = [_numeric(record.get("close")) for record in records]
    closes = [value for value in closes if value is not None]

    def average(window: int) -> float | None:
        if len(closes) < window:
            return None
        return round(sum(closes[-window:]) / window, 6)

    return {"ma5": average(5), "ma10": average(10)}


def calculate_window_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    clean = [record for record in records if _numeric(record.get("close")) is not None]
    if not clean:
        return {
            "return_5d": None,
            "return_10d": None,
            "return_20d": None,
            "positive_days_20d": None,
            "amount_5d_vs_20d": None,
            "distance_from_20d_high": None,
        }

    def period_return(days: int) -> float | None:
        if len(clean) < days + 1:
            return None
        start = _numeric(clean[-(days + 1)].get("close"))
        end = _numeric(clean[-1].get("close"))
        if not start or end is None:
            return None
        return (end / start - 1) * 100

    trailing_20 = clean[-20:]
    trailing_start = len(clean) - len(trailing_20)
    positive_days = 0
    for index, record in enumerate(trailing_20):
        pct = _numeric(record.get("pct_change"))
        absolute_index = trailing_start + index
        if pct is None and absolute_index > 0:
            previous = _numeric(clean[absolute_index - 1].get("close"))
            current = _numeric(record.get("close"))
            if previous and current is not None:
                pct = (current / previous - 1) * 100
        if pct is not None and pct > 0:
            positive_days += 1

    amounts_20 = [_numeric(item.get("amount")) for item in trailing_20]
    amounts_20 = [value for value in amounts_20 if value is not None]
    amounts_5 = [_numeric(item.get("amount")) for item in clean[-5:]]
    amounts_5 = [value for value in amounts_5 if value is not None]
    amount_ratio = None
    if amounts_20 and amounts_5:
        average_20 = sum(amounts_20) / len(amounts_20)
        if average_20:
            amount_ratio = (sum(amounts_5) / len(amounts_5)) / average_20

    highs = [_numeric(item.get("high")) for item in trailing_20]
    highs = [value for value in highs if value is not None]
    last_close = _numeric(clean[-1].get("close"))
    distance = None
    if highs and last_close is not None and max(highs):
        distance = (last_close / max(highs) - 1) * 100

    return {
        "return_5d": period_return(5),
        "return_10d": period_return(10),
        "return_20d": period_return(20),
        "positive_days_20d": positive_days,
        "amount_5d_vs_20d": amount_ratio,
        "distance_from_20d_high": distance,
    }


def determine_completeness(
    *,
    mode: str,
    now: datetime,
    trade_date: str,
    latest_history_date: str | None,
    market_coverage: float,
    board_history_complete: bool,
) -> dict[str, Any]:
    reasons: list[str] = []
    status = "complete"
    if mode == "auction" and now.time() < AUCTION_READY_TIME:
        return {"status": "failed", "reasons": ["9:25 前禁止生成竞价确认数据"]}
    if mode == "post_close" and now.time() < POST_CLOSE_READY_TIME:
        status = "partial"
        reasons.append("17:10 前日线可能尚未完成更新")
    if latest_history_date != trade_date:
        status = "partial"
        reasons.append(f"最新历史交易日 {latest_history_date or '缺失'} 与目标交易日 {trade_date} 不一致")
    if market_coverage < MIN_MARKET_COVERAGE:
        status = "partial"
        reasons.append(f"全市场有效覆盖率 {market_coverage:.2%} 低于 {MIN_MARKET_COVERAGE:.0%}")
    if not board_history_complete:
        status = "partial"
        reasons.append("板块历史数据不完整")
    return {"status": status, "reasons": reasons}


def _records_from_dataframe(frame: Any, mapping: dict[str, str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if frame is None or getattr(frame, "empty", True):
        return records
    for source in frame.to_dict(orient="records"):
        record = {target: normalize_scalar(source.get(column)) for target, column in mapping.items()}
        records.append(record)
    return records


def _to_iso_date(value: Any) -> str | None:
    value = normalize_scalar(value)
    if value is None:
        return None
    text = str(value).split(" ")[0].replace("/", "-")
    if re.fullmatch(r"\d{8}", text):
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return text


class Provider(Protocol):
    name: str

    def health(self) -> dict[str, Any]: ...
    def fetch_indices(self) -> list[dict[str, Any]]: ...
    def fetch_market_spot(self) -> list[dict[str, Any]]: ...
    def fetch_limit_pools(self, trade_date: str) -> dict[str, list[dict[str, Any]]]: ...
    def fetch_boards(self, trade_date: str) -> dict[str, list[dict[str, Any]]]: ...
    def fetch_stock_details(self, symbols: list[str], trade_date: str) -> list[dict[str, Any]]: ...


class AKShareProvider:
    name = "akshare"

    def __init__(self, board_limit: int = 10, constituent_limit: int = 10):
        self.board_limit = board_limit
        self.constituent_limit = constituent_limit
        self._spot_cache: list[dict[str, Any]] | None = None
        try:
            import akshare as ak  # type: ignore
        except ImportError as exc:
            raise RuntimeError("未安装 akshare；请执行 python -m pip install -r requirements.txt") from exc
        self.ak = ak

    def health(self) -> dict[str, Any]:
        version = getattr(self.ak, "__version__", "unknown")
        try:
            indices = self.fetch_indices()
        except Exception as exc:
            return {"ok": False, "version": version, "endpoint_ok": False, "error": redact_secrets(exc)}
        return {"ok": bool(indices), "version": version, "endpoint_ok": bool(indices)}

    def fetch_indices(self) -> list[dict[str, Any]]:
        frame = self.ak.stock_zh_index_spot_em(symbol="沪深重要指数")
        rows = _records_from_dataframe(
            frame,
            {
                "code": "代码",
                "name": "名称",
                "price": "最新价",
                "pct_change": "涨跌幅",
                "amount": "成交额",
            },
        )
        wanted = {"000001", "399001", "399006", "000688"}
        return [row for row in rows if str(row.get("code")) in wanted]

    def fetch_market_spot(self) -> list[dict[str, Any]]:
        if self._spot_cache is not None:
            return self._spot_cache
        frame = self.ak.stock_zh_a_spot_em()
        rows = _records_from_dataframe(
            frame,
            {
                "code": "代码",
                "name": "名称",
                "price": "最新价",
                "pct_change": "涨跌幅",
                "amount": "成交额",
                "turnover": "换手率",
                "open": "今开",
                "high": "最高",
                "low": "最低",
                "previous_close": "昨收",
            },
        )
        self._spot_cache = rows
        return rows

    def fetch_limit_pools(self, trade_date: str) -> dict[str, list[dict[str, Any]]]:
        date_value = trade_date.replace("-", "")
        calls = {
            "limit_up": self.ak.stock_zt_pool_em,
            "limit_down": self.ak.stock_zt_pool_dtgc_em,
            "previous": self.ak.stock_zt_pool_previous_em,
            "strong": self.ak.stock_zt_pool_strong_em,
            "broken": self.ak.stock_zt_pool_zbgc_em,
        }
        result: dict[str, list[dict[str, Any]]] = {}
        for name, function in calls.items():
            frame = function(date=date_value)
            rows = []
            if frame is not None and not frame.empty:
                for source in frame.to_dict(orient="records"):
                    rows.append({str(key): normalize_scalar(value) for key, value in source.items()})
            result[name] = rows
        return result

    def _board_history(self, kind: str, name: str, trade_date: str) -> list[dict[str, Any]]:
        end = trade_date.replace("-", "")
        start = (datetime.strptime(end, "%Y%m%d") - timedelta(days=60)).strftime("%Y%m%d")
        function = (
            self.ak.stock_board_industry_hist_em
            if kind == "industries"
            else self.ak.stock_board_concept_hist_em
        )
        frame = function(symbol=name, start_date=start, end_date=end, period="日k", adjust="")
        rows = _records_from_dataframe(
            frame,
            {
                "date": "日期",
                "open": "开盘",
                "close": "收盘",
                "high": "最高",
                "low": "最低",
                "pct_change": "涨跌幅",
                "amount": "成交额",
                "turnover": "换手率",
            },
        )
        for row in rows:
            row["date"] = _to_iso_date(row.get("date"))
        return rows

    def _board_constituents(self, kind: str, name: str) -> list[dict[str, Any]]:
        function = (
            self.ak.stock_board_industry_cons_em
            if kind == "industries"
            else self.ak.stock_board_concept_cons_em
        )
        frame = function(symbol=name)
        rows = _records_from_dataframe(
            frame,
            {"code": "代码", "name": "名称", "price": "最新价", "pct_change": "涨跌幅", "amount": "成交额"},
        )
        rows.sort(key=lambda item: _numeric(item.get("pct_change")) or -9999, reverse=True)
        return rows[: self.constituent_limit]

    def _fetch_board_kind(self, kind: str, trade_date: str) -> list[dict[str, Any]]:
        function = self.ak.stock_board_industry_name_em if kind == "industries" else self.ak.stock_board_concept_name_em
        frame = function()
        rows = _records_from_dataframe(
            frame,
            {"name": "板块名称", "code": "板块代码", "pct_change": "涨跌幅", "amount": "成交额"},
        )
        rows.sort(key=lambda item: _numeric(item.get("pct_change")) or -9999, reverse=True)
        output = []
        for row in rows[: self.board_limit]:
            name = str(row.get("name") or "")
            history = self._board_history(kind, name, trade_date)
            output.append(
                {
                    **row,
                    "history": history,
                    "metrics": calculate_window_metrics(history),
                    "constituents": self._board_constituents(kind, name),
                }
            )
        return output

    def fetch_boards(self, trade_date: str) -> dict[str, list[dict[str, Any]]]:
        return {
            "industries": self._fetch_board_kind("industries", trade_date),
            "concepts": self._fetch_board_kind("concepts", trade_date),
        }

    def fetch_stock_details(self, symbols: list[str], trade_date: str) -> list[dict[str, Any]]:
        spot_by_code = {str(row.get("code")): row for row in self.fetch_market_spot()}
        end = trade_date.replace("-", "")
        start = (datetime.strptime(end, "%Y%m%d") - timedelta(days=60)).strftime("%Y%m%d")
        details = []
        for symbol in symbols:
            normalized = normalize_stock_code(symbol)
            code = normalized.split(".")[0]
            frame = self.ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start,
                end_date=end,
                adjust="qfq",
            )
            history = _records_from_dataframe(
                frame,
                {
                    "date": "日期",
                    "open": "开盘",
                    "close": "收盘",
                    "high": "最高",
                    "low": "最低",
                    "pct_change": "涨跌幅",
                    "amount": "成交额",
                    "turnover": "换手率",
                },
            )
            for row in history:
                row["date"] = _to_iso_date(row.get("date"))
            details.append(
                {
                    "symbol": normalized,
                    "quote": spot_by_code.get(code),
                    "history": history,
                    "ma": calculate_ma(history),
                }
            )
        return details


class ZhituProvider:
    """Optional paid fallback for quotes and K-lines; never logs the token."""

    name = "zhitu"
    base_url = "https://api.zhituapi.com"

    def __init__(self, token: str | None = None, timeout: int = 20):
        self.token = token or os.getenv("ZHITU_API_TOKEN")
        self.timeout = timeout
        if not self.token:
            raise RuntimeError("未配置 ZHITU_API_TOKEN")

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        query = {**(params or {}), "token": self.token}
        url = f"{self.base_url}{path}?{urllib.parse.urlencode(query)}"
        request = urllib.request.Request(url, headers={"User-Agent": "CodexPremarketSkill/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            labels = {401: "当日额度耗尽", 402: "Token 无效", 404: "资源不存在", 429: "请求频率超限"}
            raise RuntimeError(f"智兔 API {exc.code}: {labels.get(exc.code, '请求失败')}") from exc

    def health(self) -> dict[str, Any]:
        data = self._get("/hz/real/ssjy/000001.SH")
        return {"ok": bool(data), "version": "api", "timestamp": data.get("t") if isinstance(data, dict) else None}

    def fetch_indices(self) -> list[dict[str, Any]]:
        names = {
            "000001.SH": "上证指数",
            "399001.SZ": "深证成指",
            "399006.SZ": "创业板指",
            "000688.SH": "科创50",
        }
        rows = []
        for code, name in names.items():
            data = self._get(f"/hz/real/ssjy/{code}")
            rows.append(
                {
                    "code": code.split(".")[0],
                    "name": name,
                    "price": normalize_scalar(data.get("p")),
                    "pct_change": normalize_scalar(data.get("pc")),
                    "amount": normalize_scalar(data.get("cje")),
                    "timestamp": normalize_scalar(data.get("t")),
                }
            )
        return rows

    def fetch_market_spot(self) -> list[dict[str, Any]]:
        data = self._get("/hs/public/realall")
        if not isinstance(data, list):
            raise RuntimeError("智兔全市场接口返回格式异常")
        return [
            {
                "code": str(row.get("dm", "")).replace("sh", "").replace("sz", "").replace("bj", ""),
                "name": normalize_scalar(row.get("mc")),
                "price": normalize_scalar(row.get("p")),
                "pct_change": normalize_scalar(row.get("pc")),
                "amount": normalize_scalar(row.get("cje")),
                "turnover": normalize_scalar(row.get("hs")),
            }
            for row in data
        ]

    @staticmethod
    def _data_rows(payload: Any) -> list[Any]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("data", "list", "items"):
                if isinstance(payload.get(key), list):
                    return payload[key]
        return []

    def fetch_stock_details(self, symbols: list[str], trade_date: str) -> list[dict[str, Any]]:
        details = []
        for symbol in symbols:
            normalized = normalize_stock_code(symbol)
            quote = self._get(f"/hs/real/ssjy/{normalized}")
            payload = self._get(f"/hs/latest/{normalized}/d/n", {"limit": 60})
            history = []
            for source in self._data_rows(payload):
                if not isinstance(source, dict):
                    continue
                row = {
                    "date": _to_iso_date(source.get("d") or source.get("date") or source.get("t")),
                    "open": normalize_scalar(source.get("o") or source.get("open")),
                    "close": normalize_scalar(source.get("c") or source.get("close")),
                    "high": normalize_scalar(source.get("h") or source.get("high")),
                    "low": normalize_scalar(source.get("l") or source.get("low")),
                    "pct_change": normalize_scalar(source.get("pc") or source.get("pct_change")),
                    "amount": normalize_scalar(source.get("cje") or source.get("amount")),
                    "turnover": normalize_scalar(source.get("hs") or source.get("turnover")),
                }
                history.append(row)
            history.sort(key=lambda item: str(item.get("date") or ""))
            details.append(
                {
                    "symbol": normalized,
                    "quote": quote if isinstance(quote, dict) else None,
                    "history": history,
                    "ma": calculate_ma(history),
                }
            )
        return details

class ResilientProvider:
    """Use an optional secondary provider only when the primary call fails."""

    def __init__(self, primary: Provider, fallback: Any | None = None, secrets: Iterable[str] | None = None):
        self.primary = primary
        self.fallback = fallback
        self.name = primary.name
        self.used_providers = [primary.name]
        self.warnings: list[str] = []
        self.secrets = list(secrets or [])

    def health(self) -> dict[str, Any]:
        return self.primary.health()

    def _call(self, method: str, *args: Any) -> Any:
        try:
            return getattr(self.primary, method)(*args)
        except Exception as primary_error:
            fallback_method = getattr(self.fallback, method, None) if self.fallback else None
            if fallback_method is None:
                raise
            try:
                result = fallback_method(*args)
            except Exception as fallback_error:
                message = f"{method}: primary={primary_error}; fallback={fallback_error}"
                raise RuntimeError(redact_secrets(message, self.secrets)) from fallback_error
            if self.fallback.name not in self.used_providers:
                self.used_providers.append(self.fallback.name)
            self.warnings.append(
                redact_secrets(f"{method}: {self.primary.name} 失败，已回退到 {self.fallback.name}: {primary_error}", self.secrets)
            )
            return result

    def fetch_indices(self) -> list[dict[str, Any]]:
        return self._call("fetch_indices")

    def fetch_market_spot(self) -> list[dict[str, Any]]:
        return self._call("fetch_market_spot")

    def fetch_limit_pools(self, trade_date: str) -> dict[str, list[dict[str, Any]]]:
        return self._call("fetch_limit_pools", trade_date)

    def fetch_boards(self, trade_date: str) -> dict[str, list[dict[str, Any]]]:
        return self._call("fetch_boards", trade_date)

    def fetch_stock_details(self, symbols: list[str], trade_date: str) -> list[dict[str, Any]]:
        return self._call("fetch_stock_details", symbols, trade_date)

def _latest_history_date(boards: dict[str, list[dict[str, Any]]]) -> str | None:
    dates = []
    for kind in ("industries", "concepts"):
        for board in boards.get(kind, []):
            history = board.get("history") or []
            if history and history[-1].get("date"):
                dates.append(str(history[-1]["date"]))
    return min(dates) if dates else None


def _board_history_complete(boards: dict[str, list[dict[str, Any]]], trade_date: str) -> bool:
    for kind in ("industries", "concepts"):
        rows = boards.get(kind) or []
        if not rows:
            return False
        for board in rows:
            history = board.get("history") or []
            if len(history) < 21 or str(history[-1].get("date")) != trade_date:
                return False
    return True


def create_provider(board_limit: int = 10) -> ResilientProvider:
    """Create AKShare primary provider and enable Zhitu only when a token exists."""
    primary = AKShareProvider(board_limit=board_limit)
    token = os.getenv("ZHITU_API_TOKEN")
    fallback = ZhituProvider(token=token) if token else None
    return ResilientProvider(primary, fallback, secrets=[token or ""])

def build_snapshot(
    *,
    provider: Provider,
    mode: str,
    now: datetime,
    trade_date: str,
    symbols: list[str],
) -> dict[str, Any]:
    errors: list[str] = []
    providers = list(getattr(provider, "used_providers", [provider.name]))

    def collect(label: str, function: Any, default: Any) -> Any:
        try:
            return function()
        except Exception as exc:  # Boundary: all provider failures become structured errors.
            errors.append(redact_secrets(f"{label}: {exc}", secrets=[os.getenv("ZHITU_API_TOKEN", "")]))
            return default

    indices = collect("指数行情失败", provider.fetch_indices, [])
    market_rows = collect("全市场行情失败", provider.fetch_market_spot, [])
    pools = collect("涨跌股池失败", lambda: provider.fetch_limit_pools(trade_date), {})
    boards = collect("板块数据失败", lambda: provider.fetch_boards(trade_date), {"industries": [], "concepts": []})
    stocks = collect("候选股数据失败", lambda: provider.fetch_stock_details(symbols, trade_date), [])

    valid_changes = [_numeric(row.get("pct_change")) for row in market_rows]
    valid_changes = [value for value in valid_changes if value is not None]
    breadth = {
        "total": len(market_rows),
        "valid": len(valid_changes),
        "up": sum(value > 0 for value in valid_changes),
        "down": sum(value < 0 for value in valid_changes),
        "flat": sum(value == 0 for value in valid_changes),
        "coverage": len(valid_changes) / len(market_rows) if market_rows else 0.0,
    }
    amounts = [_numeric(row.get("amount")) for row in market_rows]
    total_amount = sum(value for value in amounts if value is not None)
    latest_date = _latest_history_date(boards)
    completeness = determine_completeness(
        mode=mode,
        now=now,
        trade_date=trade_date,
        latest_history_date=latest_date,
        market_coverage=breadth["coverage"],
        board_history_complete=_board_history_complete(boards, trade_date),
    )
    if errors and completeness["status"] == "complete":
        completeness["status"] = "partial"
        completeness["reasons"].append("部分数据源请求失败")
    providers = list(getattr(provider, "used_providers", providers))
    warnings = list(getattr(provider, "warnings", []))

    return {
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "generated_at": now.isoformat(),
            "trade_date": trade_date,
            "mode": mode,
            "providers": providers,
            "completeness": completeness["status"],
            "completeness_reasons": completeness["reasons"],
            "errors": errors,
            "warnings": warnings,
        },
        "market": {
            "indices": indices,
            "breadth": breadth,
            "total_amount": total_amount,
            "limit_pools": pools,
        },
        "boards": boards,
        "stocks": stocks,
        "risk": {"status": "not_checked", "required_sources": REQUIRED_RISK_SOURCES},
    }


def select_latest_complete_cache(cache_dir: Path) -> dict[str, Any] | None:
    candidates = []
    if not cache_dir.exists():
        return None
    for path in cache_dir.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        meta = payload.get("meta", {})
        if meta.get("completeness") == "complete" and meta.get("trade_date"):
            candidates.append((str(meta["trade_date"]), payload))
    return max(candidates, key=lambda item: item[0])[1] if candidates else None


def _write_snapshot(snapshot: dict[str, Any], output: Path | None, cache_dir: Path) -> None:
    text = json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    if snapshot["meta"]["mode"] == "post_close":
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"{snapshot['meta']['trade_date']}.json"
        cache_file.write_text(text, encoding="utf-8")
    if output:
        print(
            json.dumps(
                {"meta": snapshot["meta"], "output": str(output)},
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )
        )
    else:
        print(text)


def _health_snapshot(now: datetime) -> dict[str, Any]:
    providers = []
    errors = []
    warnings = []
    try:
        provider = AKShareProvider(board_limit=1, constituent_limit=1)
        health = provider.health()
        providers.append({"name": provider.name, **health})
        if not health.get("ok") and health.get("error"):
            errors.append(str(health["error"]))
    except Exception as exc:
        errors.append(redact_secrets(exc))
        providers.append({"name": "akshare", "ok": False})
    if os.getenv("ZHITU_API_TOKEN"):
        try:
            provider = ZhituProvider()
            providers.append({"name": provider.name, **provider.health()})
        except Exception as exc:
            errors.append(redact_secrets(exc, secrets=[os.getenv("ZHITU_API_TOKEN", "")]))
            providers.append({"name": "zhitu", "ok": False})
    else:
        providers.append({"name": "zhitu", "ok": False, "optional": True, "reason": "未配置 ZHITU_API_TOKEN"})
    return {
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "generated_at": now.isoformat(),
            "trade_date": "",
            "mode": "health",
            "providers": providers,
            "completeness": "complete" if not errors and providers[0].get("ok") else "failed",
            "errors": errors,
            "warnings": warnings,
        },
        "market": {"indices": [], "breadth": {}, "total_amount": None, "limit_pools": {}},
        "boards": {"industries": [], "concepts": []},
        "stocks": [],
        "risk": {"status": "not_checked", "required_sources": REQUIRED_RISK_SOURCES},
    }


def _default_trade_date(now: datetime) -> str:
    current = now.date()
    if now.time() < clock_time(15, 0):
        current -= timedelta(days=1)
    while current.weekday() >= 5:
        current -= timedelta(days=1)
    return current.isoformat()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="采集盘前选股所需的A股事实数据")
    parser.add_argument("--mode", choices=("post_close", "auction", "health"), required=True)
    parser.add_argument("--date", dest="trade_date", help="目标交易日，格式 YYYY-MM-DD")
    parser.add_argument("--symbols", nargs="*", default=[], help="候选股票代码")
    parser.add_argument("--output", type=Path, help="可选JSON输出文件")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--board-limit", type=int, default=10)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    now = datetime.now().astimezone().replace(tzinfo=None)
    if args.mode == "health":
        snapshot = _health_snapshot(now)
        _write_snapshot(snapshot, args.output, args.cache_dir)
        return 0 if snapshot["meta"]["completeness"] == "complete" else 1

    if args.mode == "auction":
        cached = select_latest_complete_cache(args.cache_dir)
        if cached is None:
            snapshot = {
                "meta": {
                    "schema_version": SCHEMA_VERSION,
                    "generated_at": now.isoformat(),
                    "trade_date": "",
                    "mode": "auction",
                    "providers": [],
                    "completeness": "failed",
                    "completeness_reasons": ["未找到最近完整交易日缓存"],
                    "errors": [],
                },
                "market": {"indices": [], "breadth": {}, "total_amount": None, "limit_pools": {}},
                "boards": {"industries": [], "concepts": []},
                "stocks": [],
                "risk": {"status": "not_checked", "required_sources": REQUIRED_RISK_SOURCES},
            }
            _write_snapshot(snapshot, args.output, args.cache_dir)
            return 1
        if now.time() < AUCTION_READY_TIME:
            cached["meta"].update(
                {
                    "generated_at": now.isoformat(),
                    "mode": "auction",
                    "completeness": "failed",
                    "completeness_reasons": ["9:25 前禁止生成竞价确认数据"],
                }
            )
            _write_snapshot(cached, args.output, args.cache_dir)
            return 1
        provider = create_provider(board_limit=args.board_limit)
        cached["meta"].update({"generated_at": now.isoformat(), "mode": "auction", "providers": provider.used_providers})
        try:
            rows = provider.fetch_market_spot()
            valid = [_numeric(row.get("pct_change")) for row in rows]
            valid = [value for value in valid if value is not None]
            cached["market"]["indices"] = provider.fetch_indices()
            cached["market"]["breadth"] = {
                "total": len(rows),
                "valid": len(valid),
                "up": sum(value > 0 for value in valid),
                "down": sum(value < 0 for value in valid),
                "flat": sum(value == 0 for value in valid),
                "coverage": len(valid) / len(rows) if rows else 0.0,
            }
            cached["stocks"] = provider.fetch_stock_details(args.symbols, cached["meta"]["trade_date"])
            cached["meta"]["completeness"] = "complete"
            cached["meta"]["completeness_reasons"] = []
            cached["meta"]["providers"] = provider.used_providers
            cached["meta"]["warnings"] = provider.warnings
        except Exception as exc:
            cached["meta"]["completeness"] = "partial"
            cached["meta"].setdefault("errors", []).append(redact_secrets(exc))
        _write_snapshot(cached, args.output, args.cache_dir)
        return 0 if cached["meta"]["completeness"] == "complete" else 1

    trade_date = args.trade_date or _default_trade_date(now)
    try:
        provider = create_provider(board_limit=args.board_limit)
    except Exception as exc:
        snapshot = {
            "meta": {
                "schema_version": SCHEMA_VERSION,
                "generated_at": now.isoformat(),
                "trade_date": trade_date,
                "mode": args.mode,
                "providers": [],
                "completeness": "failed",
                "completeness_reasons": ["AKShare不可用"],
                "errors": [redact_secrets(exc)],
            },
            "market": {"indices": [], "breadth": {}, "total_amount": None, "limit_pools": {}},
            "boards": {"industries": [], "concepts": []},
            "stocks": [],
            "risk": {"status": "not_checked", "required_sources": REQUIRED_RISK_SOURCES},
        }
        _write_snapshot(snapshot, args.output, args.cache_dir)
        return 1
    snapshot = build_snapshot(
        provider=provider,
        mode=args.mode,
        now=now,
        trade_date=trade_date,
        symbols=args.symbols,
    )
    _write_snapshot(snapshot, args.output, args.cache_dir)
    return 0 if snapshot["meta"]["completeness"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
