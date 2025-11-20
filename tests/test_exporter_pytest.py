from datetime import date, timedelta
from pathlib import Path

import pytest
from pytest import MonkeyPatch

import family_schedulekit.exporter as exporter
from family_schedulekit.exporter import (
    ExportPlan,
    _csv_lines,
    _daterange,
    _ical_for_records,
    _map_guardian_names_in_records,
    _swap_messages_for_records,
    resolve_range,
    write_exports,
)
from family_schedulekit.models import ScheduleConfigModel
from family_schedulekit.resources import load_default_config

CFG = load_default_config()
START_DATE = date(2025, 2, 3)  # Monday CW6
RECORDS = resolve_range(START_DATE, 1, CFG)


@pytest.fixture
def sample_records() -> list[dict]:
    return [
        {
            "date": START_DATE.isoformat(),
            "guardian": "guardian_2",
            "handoff": "school",
            "calendar_week": 6,
            "weekday": "monday",
            "calendar_week_system": "ISO8601",
        }
    ]


def test_export_plan_dataclass():
    plan = ExportPlan(start=date(2025, 1, 1), weeks=4, outdir=Path("out"))
    assert plan.start == date(2025, 1, 1)
    assert plan.weeks == 4
    assert plan.outdir == Path("out")
    assert plan.formats == ("csv", "json", "jsonl", "ics", "md")


def test_daterange():
    start = date(2025, 1, 1)
    dates = list(_daterange(start, 3))
    assert dates == [
        start,
        start + timedelta(days=1),
        start + timedelta(days=2),
    ]


def test_resolve_range():
    records = resolve_range(START_DATE, 1, CFG)
    assert len(records) == 7
    first = records[0]
    assert first["iso_date"] == START_DATE.isoformat()
    assert first["weekday"] == "monday"
    assert first["calendar_week_system"] == "ISO8601"
    assert "guardian" in first
    assert first["handoff"] is not None  # school handoff expected


def test_resolve_range_with_swap():
    cfg_dict = CFG.model_dump()
    cfg_dict["swaps"] = {"2025-02-03": {"guardian": "guardian_1", "note": "Test swap"}}
    swap_cfg = ScheduleConfigModel.model_validate(cfg_dict)
    records = resolve_range(START_DATE, 1, swap_cfg)
    first = records[0]
    assert first["is_swap"] is True
    assert first["swap_note"] == "Test swap"
    assert "swap_color" not in first  # No color specified


def test_csv_lines(sample_records):
    lines = _csv_lines(sample_records)
    assert len(lines) == 2
    assert lines[0] == "iso_date,weekday,calendar_week,guardian,handoff"
    first_row = lines[1].split(",")
    assert first_row[0] == "2025-02-03"  # Unquoted ISO date
    assert first_row[-1] == "school"  # Unquoted handoff


@pytest.mark.parametrize(
    "record,expected_row",
    [
        (
            {
                "date": "2025-02-03",
                "weekday": "monday",
                "calendar_week": 6,
                "guardian": "guardian_2",
                "handoff": "school",
            },
            ["2025-02-03", "monday", "6", "guardian_2", "school"],
        ),
        (
            {
                "date": "2025-02-04",
                "weekday": "tuesday",
                "calendar_week": 6,
                "guardian": "guardian_1",
                "handoff": None,
            },
            ["2025-02-04", "tuesday", "6", "guardian_1", ""],
        ),
    ],
)
def test_csv_lines_escaping(sample_records, record, expected_row):
    # Replace first record for test
    test_records = [record]
    lines = _csv_lines(test_records)
    first_row = lines[1].split(",")
    assert first_row == expected_row


def test_ical_for_records(sample_records):
    ical = _ical_for_records(sample_records)
    assert "BEGIN:VCALENDAR" in ical
    assert "PRODID:-//family-schedulekit//EN" in ical
    assert "BEGIN:VEVENT" in ical
    assert "SUMMARY:Monday: Guardian_2" in ical
    assert "DESCRIPTION:ISO week 6 (ISO8601)" in ical
    assert "DTSTART;VALUE=DATE:20250203" in ical
    assert "END:VCALENDAR" in ical


def test_swap_messages_for_records():
    # Monday with school handoff
    monday_record = {
        "date": "2025-02-03",
        "guardian": "guardian_2",
        "handoff": "school",
        "weekday": "monday",
    }
    messages = _swap_messages_for_records([monday_record])
    assert len(messages) == 1
    msg = messages[0]
    assert "guardian_2 has the kids on monday 2025-02-03" in msg["input"]
    assert "Quick reminder: Guardian_2 has the kids" in msg["ideal"]

    # Sunday with special handoff
    sunday_record = {
        "date": "2025-02-09",
        "guardian": "guardian_1",
        "handoff": "guardian_2_to_guardian_1_by_1pm",
        "weekday": "sunday",
    }
    messages = _swap_messages_for_records([sunday_record])
    assert len(messages) == 1
    msg = messages[0]
    assert "drop-off from Guardian 2 to Guardian 1 by 1 PM" in msg["input"]


def test_map_guardian_names_in_records():
    mapped = _map_guardian_names_in_records(RECORDS, CFG)
    for rec in mapped:
        guardian = rec["guardian"]
        assert guardian in (CFG.parties.guardian_1, CFG.parties.guardian_2)
        assert isinstance(guardian, str)


@pytest.mark.parametrize(
    "formats,expected_files",
    [
        (("csv",), ["schedule_2025-02-03_1w.csv"]),
        (("json", "ics"), ["schedule_2025-02-03_1w.json", "calendar_2025-02-03_1w.ics"]),
        (("jsonl",), ["messages_2025-02-03_1w.jsonl"]),
    ],
)
def test_write_exports_formats(tmp_path, formats, expected_files):
    plan = ExportPlan(start=START_DATE, weeks=1, outdir=tmp_path, formats=formats)
    paths = write_exports(plan, CFG)
    for fmt in formats:
        assert fmt in paths
        path = paths[fmt]
        assert path.exists()
        assert path.name in expected_files
        assert path.stat().st_size > 0


def mock_render(records, start, weeks, path, **kwargs):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n")


def test_write_exports_png(tmp_path, monkeypatch: MonkeyPatch):
    # Mock visualizer to avoid Pillow deps in tests
    monkeypatch.setattr("family_schedulekit.visualizer.render_schedule_image", mock_render)

    plan = ExportPlan(start=START_DATE, weeks=1, outdir=tmp_path, formats=("png",))
    paths = write_exports(plan, CFG)
    assert "png" in paths
    png_path = paths["png"]
    assert png_path.exists()
    assert png_path.name == "visual_2025-02-03_1w.png"


def test_write_exports_full(tmp_path, monkeypatch: MonkeyPatch):
    monkeypatch.setattr("family_schedulekit.visualizer.render_schedule_image", mock_render)
    plan = ExportPlan(start=START_DATE, weeks=1, outdir=tmp_path, formats=("csv", "json", "jsonl", "ics", "md", "png"))
    paths = write_exports(plan, CFG)
    assert set(paths.keys()) == {"csv", "json", "jsonl", "ics", "md", "png"}
    for path in paths.values():
        assert path.exists()
        assert path.stat().st_size > 0


def test_write_exports_custom_start_weekday(tmp_path, monkeypatch: MonkeyPatch):
    monkeypatch.setattr("family_schedulekit.visualizer.render_schedule_image", mock_render)
    plan = ExportPlan(start=START_DATE, weeks=1, outdir=tmp_path, formats=("png",))
    paths = write_exports(plan, CFG, start_weekday_override="sunday")
    assert "png" in paths
