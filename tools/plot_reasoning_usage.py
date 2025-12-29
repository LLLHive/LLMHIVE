#!/usr/bin/env python3
"""
plot_reasoning_usage.py

Reasoning Strategy Usage Dashboard
- Works with SIMULATED data by default.
- Can read REAL logs from a JSONL/CSV file via --log.
- If running headless (no GUI), it will save a PNG instead of calling plt.show().

Examples:
  python tools/plot_reasoning_usage.py
  python tools/plot_reasoning_usage.py --save tools/reasoning_usage.png
  python tools/plot_reasoning_usage.py --log logs/orchestrator_trace.jsonl
  python tools/plot_reasoning_usage.py --log logs/orchestrator_trace.jsonl --since-days 14 --save tools/reasoning_usage_14d.png
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# Must set matplotlib backend BEFORE importing pyplot when headless.
HEADLESS = (sys.platform != "darwin") and (os.environ.get("DISPLAY", "") == "")
FORCE_HEADLESS = os.environ.get("LLMHIVE_HEADLESS", "").lower() in ("1", "true", "yes")

import matplotlib
if HEADLESS or FORCE_HEADLESS:
    matplotlib.use("Agg")

import matplotlib.pyplot as plt


DEFAULT_STRATEGIES = [
    "chain_of_thought",
    "self_consistency",
    "tree_of_thought",
    "reflexion",
    "react",
    "retrieval_augmented_generation",
    "debate",
    "self_refine",
]


def _parse_timestamp(value: str) -> datetime | None:
    """Parse timestamp from common formats. Returns None if cannot parse."""
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None

    # Try ISO first
    try:
        # Handles "2025-12-26T18:00:00" and variants
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        pass

    # Try common fallback formats
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            continue

    return None


def load_from_log(log_path: Path, since_days: int) -> pd.DataFrame:
    """
    Load reasoning usage from a log file.
    Supported:
      - JSONL (one JSON per line)
      - CSV

    Expected fields (best-effort):
      timestamp: one of ["timestamp","ts","time","created_at","datetime"]
      strategy: one of ["reasoning_method","strategy","strategy_name","method","reasoning_strategy"]
    """
    if not log_path.exists():
        raise FileNotFoundError(f"Log file not found: {log_path}")

    cutoff = datetime.now() - timedelta(days=since_days)

    # Try JSONL first if suffix suggests it
    rows = []
    suffix = log_path.suffix.lower()

    if suffix in (".jsonl", ".json"):
        import json
        with log_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue

                ts_val = None
                for k in ("timestamp", "ts", "time", "created_at", "datetime"):
                    if k in obj:
                        ts_val = obj.get(k)
                        break

                strategy_val = None
                for k in ("reasoning_method", "strategy", "strategy_name", "method", "reasoning_strategy"):
                    if k in obj:
                        strategy_val = obj.get(k)
                        break

                ts = _parse_timestamp(ts_val) if ts_val is not None else None
                if ts is None or ts < cutoff:
                    continue
                if not strategy_val:
                    continue

                rows.append({
                    "date": ts.strftime("%Y-%m-%d"),
                    "strategy": str(strategy_val).strip().lower(),
                    "count": 1
                })

    elif suffix == ".csv":
        df = pd.read_csv(log_path)
        # Find columns
        ts_col = next((c for c in df.columns if c in ("timestamp", "ts", "time", "created_at", "datetime")), None)
        st_col = next((c for c in df.columns if c in ("reasoning_method", "strategy", "strategy_name", "method", "reasoning_strategy")), None)

        if ts_col is None or st_col is None:
            raise ValueError(
                f"CSV must include timestamp and strategy columns. "
                f"Found columns={list(df.columns)}"
            )

        for _, r in df.iterrows():
            ts = _parse_timestamp(r.get(ts_col))
            if ts is None or ts < cutoff:
                continue
            strategy_val = r.get(st_col)
            if not strategy_val:
                continue
            rows.append({
                "date": ts.strftime("%Y-%m-%d"),
                "strategy": str(strategy_val).strip().lower(),
                "count": 1
            })
    else:
        raise ValueError(f"Unsupported log format: {suffix}. Use .jsonl/.json or .csv")

    if not rows:
        raise ValueError(f"No usable rows found in log (or nothing within last {since_days} days): {log_path}")

    return pd.DataFrame(rows)


def simulate_usage(since_days: int, strategies: list[str]) -> pd.DataFrame:
    """Generate simulated counts per day per strategy."""
    days = max(1, since_days)
    dates = [datetime.today() - timedelta(days=i) for i in range(days - 1, -1, -1)]
    log_data = {"date": [], "strategy": [], "count": []}

    for strategy in strategies:
        daily_counts = np.abs(np.random.normal(loc=20, scale=6, size=days)).astype(int)
        for i, count in enumerate(daily_counts):
            log_data["date"].append(dates[i].strftime("%Y-%m-%d"))
            log_data["strategy"].append(strategy)
            log_data["count"].append(int(count))

    return pd.DataFrame(log_data)


def plot_dashboard(df: pd.DataFrame, title: str, save_path: Path | None, show: bool):
    pivot = df.pivot_table(
        index="date",
        columns="strategy",
        values="count",
        aggfunc="sum",
        fill_value=0
    )

    plt.figure(figsize=(14, 6))
    for col in pivot.columns:
        plt.plot(pivot.index, pivot[col], label=col)

    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Invocation Count")
    plt.xticks(rotation=45)
    plt.legend(loc="upper left")
    plt.grid(True)
    plt.tight_layout()

    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=200)
        print(f"[OK] Saved chart to: {save_path}")

    # If headless, don't show; if show requested, show it
    if show and not (HEADLESS or FORCE_HEADLESS):
        plt.show()
    else:
        # If we didn't show and didn't save, save a default artifact to avoid "did nothing"
        if not save_path:
            default_path = Path("tools/reasoning_usage.png")
            default_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(default_path, dpi=200)
            print(f"[OK] Headless mode: saved chart to: {default_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", type=str, default="", help="Path to JSONL/CSV orchestrator trace log. If omitted, uses simulated data.")
    ap.add_argument("--since-days", type=int, default=30, help="Window size in days (default: 30).")
    ap.add_argument("--save", type=str, default="", help="Optional output PNG path.")
    ap.add_argument("--no-show", action="store_true", help="Do not open a GUI window; save PNG instead (if --save not provided, uses tools/reasoning_usage.png).")
    ap.add_argument("--strategies", type=str, default="", help="Comma-separated strategy list (simulation mode only).")

    args = ap.parse_args()

    save_path = Path(args.save) if args.save else None
    show = not args.no_show

    strategies = DEFAULT_STRATEGIES
    if args.strategies.strip():
        strategies = [s.strip().lower() for s in args.strategies.split(",") if s.strip()]

    # Load data
    if args.log.strip():
        log_path = Path(args.log).expanduser()
        print(f"[INFO] Loading from log: {log_path}")
        df = load_from_log(log_path, since_days=args.since_days)
        title = f"Reasoning Strategy Usage (Last {args.since_days} days) — from log"
    else:
        print("[INFO] No --log provided; using simulated data.")
        df = simulate_usage(since_days=args.since_days, strategies=strategies)
        title = f"Reasoning Strategy Usage (Last {args.since_days} days) — simulated"

    # Basic sanity
    if not {"date", "strategy", "count"}.issubset(df.columns):
        raise ValueError(f"DataFrame missing required columns. Found: {list(df.columns)}")

    plot_dashboard(df, title=title, save_path=save_path, show=show)


if __name__ == "__main__":
    main()
