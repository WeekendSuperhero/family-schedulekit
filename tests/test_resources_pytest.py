import pytest

from family_schedulekit import list_templates, load_default_config, load_template


def test_templates():
    names = list_templates()
    assert names == ["generic"]
    cfg = load_template("generic")
    assert cfg.calendar_week_system == "ISO8601"
    assert cfg.rules.odd_weeks.monday == "guardian_1"
    assert cfg.rules.even_weeks.monday == "guardian_2"
    assert cfg.parties.guardian_1 == "ParentA"
    assert cfg.parties.guardian_2 == "ParentB"
    assert len(cfg.parties.children) > 0
    assert cfg.handoff.default_location == "school"
    assert cfg.rules.even_weeks.sunday.modulo_rules is not None
    assert len(cfg.rules.even_weeks.sunday.modulo_rules) > 0
    assert cfg.rules.even_weeks.sunday.otherwise == "guardian_1"


def test_default_config():
    cfg = load_default_config()
    assert cfg.calendar_week_system == "ISO8601"
    assert cfg.rules.odd_weeks.monday == "guardian_1"
    assert len(cfg.parties.children) > 0


def test_load_template_invalid():
    with pytest.raises((ValueError, KeyError)):
        load_template("nonexistent")
