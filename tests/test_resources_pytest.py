from family_schedulekit import list_templates, load_template

def test_templates():
    names = list_templates()
    assert names == ["generic"]
    cfg = load_template("generic")
    assert cfg.calendar_week_system == "ISO8601"
    assert cfg.rules.weekdays.monday in ("mom","dad")
