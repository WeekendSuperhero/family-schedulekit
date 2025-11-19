from family_schedulekit import list_templates, load_template


def test_templates():
    names = list_templates()
    assert names == ["generic"]
    cfg = load_template("generic")
    assert cfg.calendar_week_system == "ISO8601"
    assert cfg.rules.odd_weeks.monday in ("guardian_1", "guardian_2")
    assert cfg.rules.even_weeks.monday in ("guardian_1", "guardian_2")
