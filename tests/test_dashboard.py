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
    calendar, indexed, cards, help_text = update_dashboard("GDP", [TERM_ORDER[0], TERM_ORDER[1]])

    assert len(calendar.data) == 2
    assert len(indexed.data) == 2
    assert len(cards) == 2
    assert "gross domestic product" in help_text
    assert any(shape["type"] == "line" for shape in indexed.layout.shapes)
