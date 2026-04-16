from __future__ import annotations

import os
import sys
from typing import cast
from pathlib import Path

import dash
import pandas as pd
import plotly.express as px
from dash import Input, Output, callback, dcc, html
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from project_config import PRESIDENCIES, PROCESSED_DATA_PATH

load_dotenv()

COLOR_MAP = {
    "Obama (2009–2017)": "#1f77b4",
    "Trump 1st Term (2017–2021)": "#d62728",
    "Biden (2021–2025)": "#2ca02c",
    "Trump 2nd Term (2025–Present)": "#ff7f0e",
}
TERM_ORDER = [term["label"] for term in sorted(PRESIDENCIES, key=lambda item: item["sort_order"])]


def load_dataset() -> pd.DataFrame:
    date_columns = ["term_start", "term_end", "latest_available_date", "observation_date", "period_end"]

    if PROCESSED_DATA_PATH.exists():
        dataset = cast(pd.DataFrame, pd.read_csv(filepath_or_buffer=str(PROCESSED_DATA_PATH)))
        for column in date_columns:
            dataset[column] = pd.to_datetime(dataset[column])
        return dataset

    required_vars = ["POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST", "POSTGRES_DB"]
    if not all(os.getenv(name) for name in required_vars):
        raise FileNotFoundError(
            f"No processed dataset found at {PROCESSED_DATA_PATH} and PostgreSQL environment variables are incomplete."
        )

    from sqlalchemy import create_engine

    db_url = (
        f"postgresql+psycopg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
        f"@{os.getenv('POSTGRES_HOST')}/{os.getenv('POSTGRES_DB')}"
    )
    dataset = cast(pd.DataFrame, pd.read_sql("SELECT * FROM economic_data", create_engine(db_url)))
    for column in date_columns:
        dataset[column] = pd.to_datetime(dataset[column])
    return dataset


DATAFRAME = load_dataset()

app = dash.Dash(__name__)
server = app.server


def build_summary_cards(filtered_df: pd.DataFrame) -> list:
    latest_rows = (
        filtered_df.sort_values("observation_date")
        .groupby("presidency", as_index=False)
        .tail(1)
        .sort_values("term_start")
    )

    cards = []
    for row in latest_rows.to_dict("records"):
        cards.append(
            html.Div(
                children=[
                    html.H3(row["presidency"], style={"marginBottom": "0.4rem"}),
                    html.P(f"Latest value: {row['value']:,.2f}", style={"margin": 0}),
                    html.P(f"Indexed to start: {row['indexed_to_start']:,.1f}", style={"margin": "0.2rem 0 0 0"}),
                    html.P(f"Observations: {row['period_index']}", style={"margin": "0.2rem 0 0 0"}),
                ],
                style={
                    "flex": "1 1 220px",
                    "padding": "1rem",
                    "border": "1px solid #d9d9d9",
                    "borderRadius": "10px",
                    "backgroundColor": "#fafafa",
                },
            )
        )
    return cards


app.layout = html.Div(
    children=[
        html.H1("Economic Data Dashboard: Last 4 U.S. Presidencies"),
        html.P(
            "Compare GDP, unemployment, and CPI across Obama, Trump's first term, Biden, and Trump's current term using the latest available FRED data."
        ),
        html.Div(
            children=[
                html.Div(
                    children=[
                        html.Label("Indicator"),
                        dcc.Dropdown(
                            id="indicator-dropdown",
                            options=[
                                {"label": label, "value": label}
                                for label in DATAFRAME["indicator"].drop_duplicates().tolist()
                            ],
                            value="GDP",
                            clearable=False,
                        ),
                    ],
                    style={"flex": "1 1 280px"},
                ),
                html.Div(
                    children=[
                        html.Label("Presidencies"),
                        dcc.Dropdown(
                            id="presidency-dropdown",
                            options=[{"label": label, "value": label} for label in TERM_ORDER],
                            value=TERM_ORDER,
                            multi=True,
                        ),
                    ],
                    style={"flex": "2 1 480px"},
                ),
            ],
            style={"display": "flex", "gap": "1rem", "flexWrap": "wrap", "marginBottom": "1.5rem"},
        ),
        html.Div(id="summary-cards", style={"display": "flex", "gap": "1rem", "flexWrap": "wrap", "marginBottom": "1.5rem"}),
        dcc.Graph(id="calendar-graph"),
        dcc.Graph(id="indexed-graph"),
    ],
    style={"maxWidth": "1280px", "margin": "0 auto", "padding": "2rem"},
)


@callback(
    Output("calendar-graph", "figure"),
    Output("indexed-graph", "figure"),
    Output("summary-cards", "children"),
    Input("indicator-dropdown", "value"),
    Input("presidency-dropdown", "value"),
)
def update_dashboard(selected_indicator: str, selected_presidencies: list[str]):
    if not selected_presidencies:
        selected_presidencies = TERM_ORDER

    filtered_df = DATAFRAME[
        (DATAFRAME["indicator"] == selected_indicator) & (DATAFRAME["presidency"].isin(selected_presidencies))
    ].copy()
    filtered_df["presidency"] = pd.Categorical(filtered_df["presidency"], categories=TERM_ORDER, ordered=True)
    filtered_df = filtered_df.sort_values(["presidency", "observation_date"])

    frequency = filtered_df["frequency"].iloc[0]
    period_axis_label = "Quarters since term start" if frequency == "quarterly" else "Months since term start"

    calendar_fig = px.line(
        filtered_df,
        x="observation_date",
        y="value",
        color="presidency",
        markers=True,
        color_discrete_map=COLOR_MAP,
        category_orders={"presidency": TERM_ORDER},
        title=f"{selected_indicator}: calendar-time comparison",
        hover_data={"period_end": True, "value": ':.2f', "president": True},
    )
    calendar_fig.update_layout(template="plotly_white", legend_title_text="Presidency")
    calendar_fig.update_xaxes(title_text="Observation date")
    calendar_fig.update_yaxes(title_text=selected_indicator)

    indexed_fig = px.line(
        filtered_df,
        x="period_index",
        y="indexed_to_start",
        color="presidency",
        markers=True,
        color_discrete_map=COLOR_MAP,
        category_orders={"presidency": TERM_ORDER},
        title=f"{selected_indicator}: normalized to 100 at the start of each term",
        hover_data={"value": ':.2f', "change_from_start": ':.2f', "president": True},
    )
    indexed_fig.update_layout(template="plotly_white", legend_title_text="Presidency")
    indexed_fig.update_xaxes(title_text=period_axis_label)
    indexed_fig.update_yaxes(title_text="Index (start of term = 100)")

    return calendar_fig, indexed_fig, build_summary_cards(filtered_df)


if __name__ == '__main__':
    app.run(debug=True)
