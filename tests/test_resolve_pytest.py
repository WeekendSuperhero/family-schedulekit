from datetime import date

from family_schedulekit import iso_week, load_default_config, resolve_for_date

CFG = load_default_config()


def test_iso_week_known():
    assert iso_week(date(2025, 2, 9)) == 6  # CW6
    assert iso_week(date(2025, 2, 23)) == 8  # CW8


def test_weekday_assignments():
    res = resolve_for_date(date(2025, 2, 3), CFG)  # Monday CW6
    assert res["guardian"] == "guardian_1" and res["handoff"] == "school"
    res = resolve_for_date(date(2025, 2, 4), CFG)  # Tuesday CW6
    assert res["guardian"] == "guardian_2" and res["handoff"] == "school"


def test_weekend_even_cw6():
    res = resolve_for_date(date(2025, 2, 7), CFG)  # Friday CW6 (guardian_2 has Thu & Fri, no change)
    assert res["guardian"] == "guardian_2" and res["handoff"] is None
    res = resolve_for_date(date(2025, 2, 8), CFG)  # Saturday CW6
    assert res["guardian"] == "guardian_2" and res["handoff"] is None
    res = resolve_for_date(date(2025, 2, 9), CFG)  # Sunday CW6
    assert res["guardian"] == "guardian_1" and res["handoff"] is None


def test_weekend_even_cw8_sunday_exception():
    res = resolve_for_date(date(2025, 2, 21), CFG)  # Friday CW8 (guardian_2 has Thu & Fri, no change)
    assert res["guardian"] == "guardian_2" and res["handoff"] is None
    res = resolve_for_date(date(2025, 2, 23), CFG)  # Sunday CW8
    assert res["guardian"] == "guardian_2" and res["handoff"] == "guardian_2_to_guardian_1_by_1pm"


def test_odd_week_full_guardian_1():
    res = resolve_for_date(date(2025, 1, 31), CFG)  # Friday CW5 (odd week)
    assert res["guardian"] == "guardian_1"


def test_swap_basic():
    """Test basic swap functionality with a simple guardian override."""
    from family_schedulekit.models import ScheduleConfigModel, SwapDate

    # Create a config with a swap
    cfg_dict = CFG.model_dump()
    cfg_dict["swaps"] = {"2025-02-10": SwapDate(guardian="guardian_2", note="Doctor appointment").model_dump()}
    test_cfg = ScheduleConfigModel(**cfg_dict)

    # Monday 2025-02-10 should normally be guardian_1's day
    res = resolve_for_date(date(2025, 2, 10), test_cfg)
    assert res["guardian"] == "guardian_2"
    assert res["is_swap"] is True
    assert res["swap_note"] == "Doctor appointment"


def test_swap_with_custom_handoff():
    """Test swap with custom handoff information."""
    from family_schedulekit.models import ScheduleConfigModel, SwapDate

    cfg_dict = CFG.model_dump()
    cfg_dict["swaps"] = {"2025-02-11": SwapDate(guardian="guardian_1", handoff="at guardian_2's house by 6pm", note="Trade for vacation").model_dump()}
    test_cfg = ScheduleConfigModel(**cfg_dict)

    # Tuesday 2025-02-11 should normally be guardian_2's day
    res = resolve_for_date(date(2025, 2, 11), test_cfg)
    assert res["guardian"] == "guardian_1"
    assert res["handoff"] == "at guardian_2's house by 6pm"
    assert res["is_swap"] is True
    assert res["swap_note"] == "Trade for vacation"


def test_no_swap_returns_false():
    """Test that regular days return is_swap=False."""
    res = resolve_for_date(date(2025, 2, 3), CFG)  # Regular Monday
    assert res["is_swap"] is False
    assert res["swap_note"] is None
