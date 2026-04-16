from __future__ import annotations

from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
RAW_DATA_DIR = PROJECT_ROOT / "data_ingestion"
PROCESSED_DATA_PATH = PROJECT_ROOT / "data_processing" / "economic_data.csv"
DB_TABLE_NAME = "economic_data"

INDICATORS = {
    "GDP": {
        "series_id": "GDP",
        "label": "GDP",
        "frequency": "quarterly",
        "unit": "Billions of Dollars",
    },
    "UNRATE": {
        "series_id": "UNRATE",
        "label": "Unemployment Rate",
        "frequency": "monthly",
        "unit": "Percent",
    },
    "CPIAUCSL": {
        "series_id": "CPIAUCSL",
        "label": "CPI",
        "frequency": "monthly",
        "unit": "Index 1982-1984=100",
    },
}

PRESIDENCIES = [
    {
        "key": "obama_2009",
        "label": "Obama (2009–2017)",
        "president": "Barack Obama",
        "term_number": 1,
        "start_date": "2009-01-20",
        "end_date": "2017-01-19",
        "file_stub": "obama",
        "sort_order": 1,
        "is_current": False,
    },
    {
        "key": "trump_2017",
        "label": "Trump 1st Term (2017–2021)",
        "president": "Donald Trump",
        "term_number": 1,
        "start_date": "2017-01-20",
        "end_date": "2021-01-19",
        "file_stub": "trump_first_term",
        "sort_order": 2,
        "is_current": False,
    },
    {
        "key": "biden_2021",
        "label": "Biden (2021–2025)",
        "president": "Joe Biden",
        "term_number": 1,
        "start_date": "2021-01-20",
        "end_date": "2025-01-19",
        "file_stub": "biden",
        "sort_order": 3,
        "is_current": False,
    },
    {
        "key": "trump_2025",
        "label": "Trump 2nd Term (2025–Present)",
        "president": "Donald Trump",
        "term_number": 2,
        "start_date": "2025-01-20",
        "end_date": None,
        "file_stub": "trump_second_term",
        "sort_order": 4,
        "is_current": True,
    },
]


def today_iso() -> str:
    return date.today().isoformat()

