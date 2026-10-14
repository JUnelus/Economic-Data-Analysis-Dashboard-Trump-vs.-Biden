from dashboard.app import TERM_ORDER, build_summary_cards, filter_dataset, format_value, update_dashboard


def test_filter_dataset_defaults_to_all_terms_and_sorts_rows():
    result = filter_dataset("GDP", None)

    assert result["presidency"].drop_duplicates().astype("object").tolist() == TERM_ORDER
    assert result.groupby("presidency", observed=True)["observation_date"].apply(
        lambda dates: dates.is_monotonic_increasing
    ).all()


def test_summary_cards_report_real_observation_count():
    filtered = filter_dataset("GDP", [TERM_ORDER[0]])
    cards = build_summary_cards(filtered)

    assert len(cards) == 1
    assert f"{len(filtered)} observations" in cards[0].children[-1].children


def test_value_formatting_uses_indicator_units():
    assert format_value(29_123.45, "GDP") == "$29,123.5B"
    assert format_value(4.25, "Unemployment Rate") == "4.2%"
    assert format_value(319.125, "CPI") == "319.1"


def test_dashboard_callback_builds_two_figures_and_cards():
    calendar, indexed, cards, help_text, freshness = update_dashboard("GDP", [TERM_ORDER[0], TERM_ORDER[1]])

    assert len(calendar.data) == 2
    assert len(indexed.data) == 2
    assert len(cards) == 2
    assert "gross domestic product" in help_text
    assert any(shape["type"] == "line" for shape in indexed.layout.shapes)


def test_committed_stylesheet_is_linked_and_served():
    from dashboard.app import app

    client = app.server.test_client()
    page = client.get("/")
    assert page.status_code == 200
    assert "/assets/styles.css" in page.get_data(as_text=True)
    stylesheet = client.get("/assets/styles.css")
    assert stylesheet.status_code == 200
    assert ".summary-grid" in stylesheet.get_data(as_text=True)


def test_summary_changes_are_neutral_for_all_indicators():
    for indicator in ("GDP", "Unemployment Rate", "CPI"):
        cards = build_summary_cards(filter_dataset(indicator, TERM_ORDER[1:3]))
        assert all(card.children[3].className == "card-change" for card in cards)
    cards = build_summary_cards(filter_dataset("Unemployment Rate", TERM_ORDER[1:3]))
    assert cards[0].children[3].children.startswith("+42.6%")
    assert cards[1].children[3].children.startswith("-35.9%")


def test_freshness_tracks_indicator_period_end_independently_of_term_filter():
    gdp = update_dashboard("GDP", [TERM_ORDER[0]])[-1]
    unemployment = update_dashboard("Unemployment Rate", TERM_ORDER)[-1]
    assert gdp == "GDP observations through December 2025"
    assert unemployment == "Unemployment Rate observations through March 2026"
    assert update_dashboard("CPI", TERM_ORDER)[-1] == "CPI observations through March 2026"
    assert update_dashboard("Unknown", TERM_ORDER)[-1] == "Unknown: no observations available"


def test_csv_download_only_on_click_and_respects_filters():
    import io

    import pandas as pd
    from dashboard.app import app

    client = app.server.test_client()
    client.get("/")  # Register the global Dash callbacks.
    payload = {
        "output": "download-data.data",
        "outputs": {"id": "download-data", "property": "data"},
        "inputs": [
            {"id": "download-button", "property": "n_clicks", "value": 1},
            {"id": "indicator-dropdown", "property": "value", "value": "CPI"},
            {"id": "presidency-dropdown", "property": "value", "value": [TERM_ORDER[2]]},
        ],
        "state": [],
        "changedPropIds": ["download-button.n_clicks"],
    }
    response = client.post("/_dash-update-component", json=payload)
    assert response.status_code == 200
    download = response.get_json()["response"]["download-data"]["data"]
    assert download["filename"] == "cpi_presidency_comparison.csv"
    exported = pd.read_csv(io.StringIO(download["content"]))
    assert exported["indicator"].unique().tolist() == ["CPI"]
    assert exported["presidency"].unique().tolist() == [TERM_ORDER[2]]
    assert len(exported) == len(filter_dataset("CPI", [TERM_ORDER[2]]))
    assert "Unnamed: 0" not in exported.columns
    payload["changedPropIds"] = ["indicator-dropdown.value"]
    response = client.post("/_dash-update-component", json=payload)
    assert "download-data" not in (response.get_json() or {}).get("response", {})
