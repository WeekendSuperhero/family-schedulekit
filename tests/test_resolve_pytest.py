from datetime import date

from family_schedulekit import iso_week, load_default_config, resolve_for_date

CFG = load_default_config()


def test_iso_week_known():
    assert iso_week(date(2025, 2, 9)) == 6  # CW6
    assert iso_week(date(2025, 2, 23)) == 8  # CW8


def test_weekday_assignments():
    res = resolve_for_date(date(2025, 2, 3), CFG)  # Monday CW6
    assert res["guardian"] == "mom" and res["handoff"] == "school"
    res = resolve_for_date(date(2025, 2, 4), CFG)  # Tuesday CW6
    assert res["guardian"] == "dad" and res["handoff"] == "school"


def test_weekend_even_cw6():
    res = resolve_for_date(date(2025, 2, 7), CFG)  # Friday CW6
    assert res["guardian"] == "dad" and res["handoff"] == "after_school"
    res = resolve_for_date(date(2025, 2, 8), CFG)  # Saturday CW6
    assert res["guardian"] == "dad" and res["handoff"] is None
    res = resolve_for_date(date(2025, 2, 9), CFG)  # Sunday CW6
    assert res["guardian"] == "mom" and res["handoff"] is None


def test_weekend_even_cw8_sunday_exception():
    res = resolve_for_date(date(2025, 2, 21), CFG)  # Friday CW8
    assert res["guardian"] == "dad" and res["handoff"] == "after_school"
    res = resolve_for_date(date(2025, 2, 23), CFG)  # Sunday CW8
    assert res["guardian"] == "dad" and res["handoff"] == "dad_to_mom_by_1pm"


def test_odd_week_full_mom():
    res = resolve_for_date(date(2025, 1, 31), CFG)  # Friday CW5 (odd week)
    assert res["guardian"] == "mom"
