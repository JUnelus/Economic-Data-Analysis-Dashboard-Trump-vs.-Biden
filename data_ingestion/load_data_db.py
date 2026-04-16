from __future__ import annotations

import os
import sys
from typing import cast
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from project_config import DB_TABLE_NAME, PROCESSED_DATA_PATH

load_dotenv()


def build_db_url() -> str:
    required_vars = ["POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST", "POSTGRES_DB"]
    missing = [name for name in required_vars if not os.getenv(name)]
    if missing:
        raise EnvironmentError(f"Missing PostgreSQL environment variables: {', '.join(missing)}")

    return (
        f"postgresql+psycopg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
        f"@{os.getenv('POSTGRES_HOST')}/{os.getenv('POSTGRES_DB')}"
    )


def load_processed_data() -> pd.DataFrame:
    if not PROCESSED_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Processed dataset not found at {PROCESSED_DATA_PATH}. Run data_processing/clean_data.py first."
        )

    dataframe = cast(pd.DataFrame, pd.read_csv(
        filepath_or_buffer=str(PROCESSED_DATA_PATH),
        parse_dates=["term_start", "term_end", "latest_available_date", "observation_date", "period_end"],
    ))
    return dataframe


if __name__ == "__main__":
    engine = create_engine(build_db_url())
    dataset = load_processed_data()
    dataset.to_sql(DB_TABLE_NAME, engine, if_exists="replace", index=False)

    print(f"Loaded {len(dataset)} rows into PostgreSQL table '{DB_TABLE_NAME}'.")
