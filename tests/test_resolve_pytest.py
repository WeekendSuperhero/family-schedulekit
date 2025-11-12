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
    res = resolve_for_date(date(2025, 2, 7), CFG)  # Friday CW6 (dad has Thu & Fri, no change)
    assert res["guardian"] == "dad" and res["handoff"] is None
    res = resolve_for_date(date(2025, 2, 8), CFG)  # Saturday CW6
    assert res["guardian"] == "dad" and res["handoff"] is None
    res = resolve_for_date(date(2025, 2, 9), CFG)  # Sunday CW6
    assert res["guardian"] == "mom" and res["handoff"] is None


def test_weekend_even_cw8_sunday_exception():
    res = resolve_for_date(date(2025, 2, 21), CFG)  # Friday CW8 (dad has Thu & Fri, no change)
    assert res["guardian"] == "dad" and res["handoff"] is None
    res = resolve_for_date(date(2025, 2, 23), CFG)  # Sunday CW8
    assert res["guardian"] == "dad" and res["handoff"] == "dad_to_mom_by_1pm"


def test_odd_week_full_mom():
    res = resolve_for_date(date(2025, 1, 31), CFG)  # Friday CW5 (odd week)
    assert res["guardian"] == "mom"


def test_swap_basic():
    """Test basic swap functionality with a simple guardian override."""
    from family_schedulekit.models import ScheduleConfigModel, SwapDate

    # Create a config with a swap
    cfg_dict = CFG.model_dump()
    cfg_dict["swaps"] = {"2025-02-10": SwapDate(guardian="dad", note="Doctor appointment").model_dump()}
    test_cfg = ScheduleConfigModel(**cfg_dict)

    # Monday 2025-02-10 should normally be mom's day
    res = resolve_for_date(date(2025, 2, 10), test_cfg)
    assert res["guardian"] == "dad"
    assert res["is_swap"] is True
    assert res["swap_note"] == "Doctor appointment"


def test_swap_with_custom_handoff():
    """Test swap with custom handoff information."""
    from family_schedulekit.models import ScheduleConfigModel, SwapDate

    cfg_dict = CFG.model_dump()
    cfg_dict["swaps"] = {"2025-02-11": SwapDate(guardian="mom", handoff="at dad's house by 6pm", note="Trade for vacation").model_dump()}
    test_cfg = ScheduleConfigModel(**cfg_dict)

    # Tuesday 2025-02-11 should normally be dad's day
    res = resolve_for_date(date(2025, 2, 11), test_cfg)
    assert res["guardian"] == "mom"
    assert res["handoff"] == "at dad's house by 6pm"
    assert res["is_swap"] is True
    assert res["swap_note"] == "Trade for vacation"


def test_no_swap_returns_false():
    """Test that regular days return is_swap=False."""
    res = resolve_for_date(date(2025, 2, 3), CFG)  # Regular Monday
    assert res["is_swap"] is False
    assert res["swap_note"] is None
