from datetime import date

from family_schedulekit import load_default_config, render_schedule_image
from family_schedulekit.exporter import ExportPlan, resolve_range, write_exports
from family_schedulekit.visualizer import _get_handoff_info_from_config, _parse_handoff_time


def test_render_schedule_image(tmp_path):
    cfg = load_default_config()
    start = date(2025, 2, 3)  # Monday
    records = resolve_range(start, 2, cfg)
    out = tmp_path / "schedule.png"

    render_schedule_image(records, start, 2, out)

    assert out.exists()
    assert out.stat().st_size > 0


def test_export_plan_png(tmp_path):
    cfg = load_default_config()
    plan = ExportPlan(start=date(2025, 2, 3), weeks=1, outdir=tmp_path, formats=("png",))

    paths = write_exports(plan, cfg)

    assert "png" in paths
    assert paths["png"].exists()


def test_gradient_handoff_with_config(tmp_path):
    """Test that gradient is rendered for special handoffs when config is provided."""
    cfg = load_default_config()

    # Find a date range that includes a Sunday with special handoff
    # CW8 2025 is even week, Sunday Feb 23 should have the special handoff
    start = date(2025, 2, 17)  # Monday of CW8
    records = resolve_range(start, 2, cfg)
    out = tmp_path / "gradient_schedule.png"

    # Render with config to enable gradient feature
    render_schedule_image(records, start, 2, out, config=cfg)

    assert out.exists()
    assert out.stat().st_size > 0

    # Verify that the handoff info is extracted correctly for the Sunday record
    sunday_record = next(r for r in records if r.get("weekday") == "sunday" and r.get("date") == "2025-02-23")
    handoff_info = _get_handoff_info_from_config(sunday_record, cfg)

    # Should return gradient info for this Sunday (guardian_2 -> guardian_1 at 1pm)
    assert handoff_info is not None
    from_guardian, to_guardian, hour = handoff_info
    assert from_guardian == "guardian_2"
    assert to_guardian == "guardian_1"
    assert hour == 13.0  # 1pm


def test_gradient_handoff_without_config(tmp_path):
    """Test that rendering works without config (no gradients, backward compatible)."""
    cfg = load_default_config()
    start = date(2025, 2, 17)
    records = resolve_range(start, 2, cfg)
    out = tmp_path / "no_gradient_schedule.png"

    # Render without config - should still work, just no gradients
    render_schedule_image(records, start, 2, out, config=None)

    assert out.exists()
    assert out.stat().st_size > 0


def test_get_handoff_info_from_config():
    """Test the handoff info extraction from config."""
    cfg = load_default_config()

    # Test record with special handoff
    record_with_handoff = {
        "date": "2025-02-23",
        "weekday": "sunday",
        "guardian": "guardian_2",
        "handoff": "guardian_2_to_guardian_1_by_1pm",
    }

    handoff_info = _get_handoff_info_from_config(record_with_handoff, cfg)
    assert handoff_info is not None
    from_guardian, to_guardian, hour = handoff_info
    assert from_guardian == "guardian_2"
    assert to_guardian == "guardian_1"
    assert hour == 13.0

    # Test record without special handoff
    record_without_handoff = {
        "date": "2025-02-24",
        "weekday": "monday",
        "guardian": "guardian_1",
        "handoff": "school",
    }

    handoff_info = _get_handoff_info_from_config(record_without_handoff, cfg)
    assert handoff_info is None


def test_parse_handoff_time():
    """Test the fallback handoff time parser."""
    # Test various time formats
    assert _parse_handoff_time("guardian_2_to_guardian_1_by_1pm") == 13.0
    assert _parse_handoff_time("by 2pm") == 14.0
    assert _parse_handoff_time("by 10am") == 10.0
    assert _parse_handoff_time("by_13:00") == 13.0
    assert _parse_handoff_time("15:30") == 15.5
    assert _parse_handoff_time("school") is None
