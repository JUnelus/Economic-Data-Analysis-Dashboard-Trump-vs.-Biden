from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pandas as pd
import requests
from pandas.tseries.offsets import MonthEnd, QuarterEnd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from project_config import INDICATORS, PRESIDENCIES, RAW_DATA_DIR, today_iso

FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"


def fetch_series_frame(series_id: str) -> pd.DataFrame:
    response = requests.get(FRED_CSV_URL, params={"id": series_id}, timeout=30)
    response.raise_for_status()

    frame = pd.read_csv(io.StringIO(response.text))
    frame = frame.rename(columns={"DATE": "date", series_id: "value", "observation_date": "date"})
    frame["date"] = pd.to_datetime(frame["date"])
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame = frame.dropna(subset=["value"]).sort_values("date").reset_index(drop=True)
    return frame


def add_period_end(frame: pd.DataFrame, frequency: str) -> pd.DataFrame:
    frame = frame.copy()
    if frequency == "monthly":
        frame["period_end"] = frame["date"] + MonthEnd(0)
    elif frequency == "quarterly":
        frame["period_end"] = frame["date"] + QuarterEnd(startingMonth=12)
    else:
        raise ValueError(f"Unsupported frequency: {frequency}")
    return frame


def build_payload(indicator_key: str, indicator_meta: dict, presidency: dict, term_frame: pd.DataFrame, latest_date: str) -> dict:
    effective_end = presidency["end_date"] or today_iso()
    observations = [
        {
            "date": row.date.strftime("%Y-%m-%d"),
            "period_end": row.period_end.strftime("%Y-%m-%d"),
            "value": float(row.value),
        }
        for row in term_frame.itertuples(index=False)
    ]

    return {
        "series_id": indicator_key,
        "indicator": indicator_meta["label"],
        "frequency": indicator_meta["frequency"],
        "unit": indicator_meta["unit"],
        "presidency_key": presidency["key"],
        "presidency": presidency["label"],
        "president": presidency["president"],
        "term_number": presidency["term_number"],
        "term_start": presidency["start_date"],
        "term_end": effective_end,
        "latest_available_date": latest_date,
        "source": FRED_CSV_URL,
        "count": len(observations),
        "observations": observations,
    }


def write_term_files() -> None:
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    for indicator_key, indicator_meta in INDICATORS.items():
        series_frame = add_period_end(fetch_series_frame(indicator_meta["series_id"]), indicator_meta["frequency"])
        latest_date = series_frame["period_end"].max().strftime("%Y-%m-%d")

        for presidency in PRESIDENCIES:
            term_end = pd.Timestamp(presidency["end_date"] or today_iso())
            term_start = pd.Timestamp(presidency["start_date"])
            term_frame = series_frame[
                (series_frame["period_end"] >= term_start) & (series_frame["period_end"] <= term_end)
            ].copy()

            payload = build_payload(indicator_key, indicator_meta, presidency, term_frame, latest_date)
            output_path = RAW_DATA_DIR / f"{indicator_key.lower()}_{presidency['file_stub']}.json"
            output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print(f"Saved {payload['count']:>3} rows to {output_path.name}")


if __name__ == "__main__":
    write_term_files()
    print("Latest FRED data fetched and term files regenerated successfully.")
