from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from project_config import INDICATORS, PRESIDENCIES, PROCESSED_DATA_PATH, RAW_DATA_DIR


def load_term_json(indicator_key: str, presidency: dict) -> pd.DataFrame:
	file_path = RAW_DATA_DIR / f"{indicator_key.lower()}_{presidency['file_stub']}.json"
	with file_path.open(encoding="utf-8") as file:
		payload = json.load(file)

	observations = payload.get("observations", [])
	frame = pd.DataFrame(observations)

	if frame.empty:
		return pd.DataFrame(
			columns=[
				"indicator_key",
				"indicator",
				"frequency",
				"unit",
				"presidency_key",
				"presidency",
				"president",
				"term_number",
				"term_start",
				"term_end",
				"latest_available_date",
				"observation_date",
				"period_end",
				"value",
			]
		)

	frame["indicator_key"] = indicator_key
	frame["indicator"] = payload["indicator"]
	frame["frequency"] = payload["frequency"]
	frame["unit"] = payload["unit"]
	frame["presidency_key"] = payload["presidency_key"]
	frame["presidency"] = payload["presidency"]
	frame["president"] = payload["president"]
	frame["term_number"] = payload["term_number"]
	frame["term_start"] = payload["term_start"]
	frame["term_end"] = payload["term_end"]
	frame["latest_available_date"] = payload["latest_available_date"]
	frame = frame.rename(columns={"date": "observation_date"})
	return frame[
		[
			"indicator_key",
			"indicator",
			"frequency",
			"unit",
			"presidency_key",
			"presidency",
			"president",
			"term_number",
			"term_start",
			"term_end",
			"latest_available_date",
			"observation_date",
			"period_end",
			"value",
		]
	]


def build_dataset() -> pd.DataFrame:
	frames = [
		load_term_json(indicator_key, presidency)
		for indicator_key in INDICATORS
		for presidency in PRESIDENCIES
	]
	dataset = pd.concat(frames, ignore_index=True)

	date_columns = ["term_start", "term_end", "latest_available_date", "observation_date", "period_end"]
	for column in date_columns:
		dataset[column] = pd.to_datetime(dataset[column])

	dataset["value"] = pd.to_numeric(dataset["value"], errors="coerce")
	dataset = dataset.dropna(subset=["value"]).sort_values(["indicator_key", "term_start", "observation_date"])

	dataset["period_index"] = dataset.groupby(["indicator_key", "presidency_key"]).cumcount() + 1
	dataset["index_base_value"] = dataset.groupby(["indicator_key", "presidency_key"])["value"].transform("first")
	dataset["indexed_to_start"] = (dataset["value"] / dataset["index_base_value"]) * 100
	dataset["change_from_start"] = dataset["value"] - dataset["index_base_value"]

	return dataset.reset_index(drop=True)


if __name__ == "__main__":
	dataset = build_dataset()
	PROCESSED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
	dataset.to_csv(PROCESSED_DATA_PATH, index=False)

	print(f"Saved {len(dataset)} cleaned rows to {PROCESSED_DATA_PATH}")
	print(dataset.groupby(["presidency", "indicator"]).agg(observations=("value", "size"), latest_value=("value", "last")))
