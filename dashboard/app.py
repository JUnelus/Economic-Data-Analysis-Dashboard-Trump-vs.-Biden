from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import cast

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
    "Obama (2009–2017)": "#2563eb",
    "Trump 1st Term (2017–2021)": "#dc2626",
    "Biden (2021–2025)": "#16a34a",
    "Trump 2nd Term (2025–Present)": "#ea580c",
}
TERM_ORDER = [term["label"] for term in sorted(PRESIDENCIES, key=lambda item: item["sort_order"])]
INDICATOR_HELP = {
    "GDP": "Quarterly nominal gross domestic product (billions of dollars; seasonally adjusted annual rate).",
    "Unemployment Rate": "Monthly civilian unemployment rate (percent; seasonally adjusted).",
    "CPI": "Monthly Consumer Price Index for All Urban Consumers (1982–84 = 100; seasonally adjusted).",
}


def load_dataset() -> pd.DataFrame:
    date_columns = ["term_start", "term_end", "latest_available_date", "observation_date", "period_end"]

    if PROCESSED_DATA_PATH.exists():
        dataset = cast(
            pd.DataFrame,
            pd.read_csv(filepath_or_buffer=str(PROCESSED_DATA_PATH), parse_dates=date_columns),
        )
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


def filter_dataset(indicator: str, presidencies: list[str] | None) -> pd.DataFrame:
    """Return a consistently ordered slice for the dashboard and downloads."""
    selected = presidencies or TERM_ORDER
    filtered = DATAFRAME[
        (DATAFRAME["indicator"] == indicator) & DATAFRAME["presidency"].isin(selected)
    ].copy()
    filtered["presidency"] = pd.Categorical(filtered["presidency"], categories=TERM_ORDER, ordered=True)
    return filtered.sort_values(["presidency", "observation_date"])


def format_value(value: float, indicator: str) -> str:
    if indicator == "GDP":
        return f"${value:,.1f}B"
    if indicator == "Unemployment Rate":
        return f"{value:.1f}%"
    return f"{value:,.1f}"


def build_summary_cards(filtered_df: pd.DataFrame) -> list:
    cards = []
    for presidency, group in filtered_df.groupby("presidency", observed=True, sort=False):
        group = group.sort_values("observation_date")
        first, latest = group.iloc[0], group.iloc[-1]
        percent_change = (latest["value"] / first["value"] - 1) * 100
        change_class = "positive" if percent_change >= 0 else "negative"
        cards.append(
            html.Article(
                className="summary-card",
                children=[
                    html.Div(className="card-accent", style={"backgroundColor": COLOR_MAP[str(presidency)]}),
                    html.P(str(presidency), className="card-label"),
                    html.H3(format_value(latest["value"], latest["indicator"]), className="card-value"),
                    html.P(
                        f"{percent_change:+.1f}% since first observation",
                        className=f"card-change {change_class}",
                    ),
                    html.P(
                        f"Through {latest['period_end']:%b %Y} · {len(group)} observations",
                        className="card-meta",
                    ),
                ],
            )
        )
    return cards


def empty_figure(message: str):
    figure = px.scatter()
    figure.add_annotation(text=message, showarrow=False, font={"size": 16, "color": "#64748b"})
    figure.update_layout(template="plotly_white", xaxis={"visible": False}, yaxis={"visible": False})
    return figure


app = dash.Dash(__name__, title="US Economy by Presidency")
server = app.server

app.layout = html.Div(
    className="app-shell",
    children=[
        html.Header(
            className="hero",
            children=[
                html.P("FRED ECONOMIC DATA", className="eyebrow"),
                html.H1("The U.S. economy across four presidencies"),
                html.P(
                    "Explore levels and start-of-term trajectories for GDP, unemployment, and consumer prices.",
                    className="hero-copy",
                ),
                html.Div(
                    className="freshness",
                    children=[
                        html.Span("●", className="status-dot"),
                        f"Dataset current through {DATAFRAME['latest_available_date'].max():%B %Y}",
                    ],
                ),
            ],
        ),
        html.Main(
            children=[
                html.Section(
                    className="control-panel",
                    children=[
                        html.Div(
                            className="control",
                            children=[
                                html.Label("Economic indicator", htmlFor="indicator-dropdown"),
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
                        ),
                        html.Div(
                            className="control presidency-control",
                            children=[
                                html.Label("Presidential terms", htmlFor="presidency-dropdown"),
                                dcc.Dropdown(
                                    id="presidency-dropdown",
                                    options=[{"label": label, "value": label} for label in TERM_ORDER],
                                    value=TERM_ORDER,
                                    multi=True,
                                    placeholder="Select one or more terms",
                                ),
                            ],
                        ),
                        html.Button("Download CSV", id="download-button", className="download-button"),
                        dcc.Download(id="download-data"),
                    ],
                ),
                html.P(id="indicator-help", className="indicator-help"),
                html.Section(id="summary-cards", className="summary-grid"),
                html.Section(
                    className="chart-card",
                    children=[
                        html.Div(
                            children=[
                                html.P("ABSOLUTE VALUES", className="chart-kicker"),
                                html.H2("Economic indicator over calendar time"),
                            ]
                        ),
                        dcc.Graph(id="calendar-graph", config={"displaylogo": False, "responsive": True}),
                    ],
                ),
                html.Section(
                    className="chart-card",
                    children=[
                        html.Div(
                            children=[
                                html.P("RELATIVE CHANGE", className="chart-kicker"),
                                html.H2("Each term rebased to 100"),
                                html.P(
                                    "Rebasing reveals direction and pace, but does not control for inherited conditions, policy lags, or external shocks.",
                                    className="chart-description",
                                ),
                            ]
                        ),
                        dcc.Graph(id="indexed-graph", config={"displaylogo": False, "responsive": True}),
                    ],
                ),
                html.Aside(
                    className="methodology",
                    children=[
                        html.H2("Read the comparison carefully"),
                        html.P(
                            "Observations are assigned by period end: monthly data by month-end and GDP by quarter-end. "
                            "A presidential term does not uniquely cause the economic outcomes shown here, and the current term is incomplete."
                        ),
                        html.P(
                            [
                                "Source: ",
                                html.A("Federal Reserve Economic Data (FRED)", href="https://fred.stlouisfed.org/", target="_blank"),
                                ". Values shown are the latest vintage downloaded by this project.",
                            ]
                        ),
                    ],
                ),
            ]
        ),
    ],
)


@callback(
    Output("calendar-graph", "figure"),
    Output("indexed-graph", "figure"),
    Output("summary-cards", "children"),
    Output("indicator-help", "children"),
    Input("indicator-dropdown", "value"),
    Input("presidency-dropdown", "value"),
)
def update_dashboard(selected_indicator: str, selected_presidencies: list[str] | None):
    filtered_df = filter_dataset(selected_indicator, selected_presidencies)
    if filtered_df.empty:
        empty = empty_figure("No observations match this selection.")
        return empty, empty, [], INDICATOR_HELP.get(selected_indicator, "")

    frequency = filtered_df["frequency"].iloc[0]
    period_axis_label = "Quarterly observations since term start" if frequency == "quarterly" else "Monthly observations since term start"
    unit = filtered_df["unit"].iloc[0]
    common_layout = {
        "template": "plotly_white",
        "legend_title_text": "",
        "hovermode": "x unified",
        "margin": {"l": 30, "r": 20, "t": 25, "b": 40},
        "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
    }

    calendar_fig = px.line(
        filtered_df,
        x="observation_date",
        y="value",
        color="presidency",
        color_discrete_map=COLOR_MAP,
        category_orders={"presidency": TERM_ORDER},
        hover_data={"observation_date": "|%b %Y", "value": ":,.2f", "president": True},
    )
    calendar_fig.update_layout(**common_layout)
    calendar_fig.update_traces(line={"width": 2.5})
    calendar_fig.update_xaxes(title_text="Observation date", showgrid=False)
    calendar_fig.update_yaxes(title_text=unit, gridcolor="#e2e8f0", tickformat=",.1f")

    indexed_fig = px.line(
        filtered_df,
        x="period_index",
        y="indexed_to_start",
        color="presidency",
        color_discrete_map=COLOR_MAP,
        category_orders={"presidency": TERM_ORDER},
        hover_data={"value": ":,.2f", "change_from_start": ":+.2f", "president": True},
    )
    indexed_fig.update_layout(**common_layout)
    indexed_fig.update_traces(line={"width": 2.5})
    indexed_fig.add_hline(y=100, line_dash="dot", line_color="#94a3b8")
    indexed_fig.update_xaxes(title_text=period_axis_label, showgrid=False)
    indexed_fig.update_yaxes(title_text="Index (first observation = 100)", gridcolor="#e2e8f0")

    return calendar_fig, indexed_fig, build_summary_cards(filtered_df), INDICATOR_HELP.get(selected_indicator, "")


@callback(
    Output("download-data", "data"),
    Input("download-button", "n_clicks"),
    Input("indicator-dropdown", "value"),
    Input("presidency-dropdown", "value"),
    prevent_initial_call=True,
)
def download_filtered_data(n_clicks: int | None, indicator: str, presidencies: list[str] | None):
    if not n_clicks or dash.ctx.triggered_id != "download-button":
        return dash.no_update
    export = filter_dataset(indicator, presidencies).copy()
    export["presidency"] = export["presidency"].astype("object")
    filename = f"{indicator.lower().replace(' ', '_')}_presidency_comparison.csv"
    return dcc.send_data_frame(export.to_csv, filename, index=False)


if __name__ == "__main__":
    app.run(debug=os.getenv("DASH_DEBUG", "false").lower() == "true")
