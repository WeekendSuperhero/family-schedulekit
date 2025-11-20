import json
from datetime import date
from pathlib import Path

import pytest

from family_schedulekit import load_default_config
from family_schedulekit.ai_helper import (
    _generate_ai_instructions,
    _generate_json_schema,
    export_ai_context,
    generate_ai_context,
)
from family_schedulekit.models import ScheduleConfigModel

CFG = load_default_config()


def test_generate_ai_context_defaults():
    """Test default generation with no params."""
    context = generate_ai_context()
    assert "system_description" in context
    assert "current_date" in context
    assert "parties" in context
    assert "rules_summary" in context
    assert "handoff_rules" in context
    assert "json_schema" in context
    assert "configuration" in context
    assert "resolved_examples" in context
    assert len(context["resolved_examples"]) == 4
    assert "decision_examples" in context
    assert "ai_instructions" in context


def test_generate_ai_context_no_examples():
    """Test without examples."""
    context = generate_ai_context(include_examples=False)
    assert "resolved_examples" not in context
    assert "decision_examples" not in context


def test_generate_ai_context_no_schema():
    """Test without schema."""
    context = generate_ai_context(include_schema=False)
    assert "json_schema" not in context
    assert "configuration" not in context


def test_generate_ai_context_custom_date():
    """Test with custom target_date."""
    target = date(2025, 2, 3)  # Known Monday CW6
    context = generate_ai_context(target_date=target, weeks_ahead=1)
    assert context["current_date"] == "2025-02-03"
    examples = context["resolved_examples"]
    assert len(examples) == 1
    assert examples[0]["week_start"] == "2025-02-03"
    assert examples[0]["calendar_week"] == 6


def test_generate_ai_context_custom_config():
    """Test with custom config."""
    custom_cfg = ScheduleConfigModel.model_validate(
        {
            "parties": {"guardian_1": "Alice", "guardian_2": "Bob", "children": ["Child"]},
            "calendar_week_system": "ISO8601",
            "handoff": {"default_location": "home"},
            "rules": {
                "odd_weeks": {
                    "monday": "guardian_1",
                    "tuesday": "guardian_1",
                    "wednesday": "guardian_1",
                    "thursday": "guardian_1",
                    "friday": "guardian_1",
                    "saturday": "guardian_1",
                    "sunday": "guardian_1",
                },
                "even_weeks": {
                    "monday": "guardian_2",
                    "tuesday": "guardian_1",
                    "wednesday": "guardian_2",
                    "thursday": "guardian_1",
                    "friday": "guardian_2",
                    "saturday": "guardian_2",
                    "sunday": {"otherwise": "guardian_1"},
                },
            },
        }
    )
    context = generate_ai_context(config=custom_cfg)
    assert context["parties"]["guardian_1"] == "Alice"
    assert context["parties"]["guardian_2"] == "Bob"


def test_rules_summary_content():
    """Verify rules summary has expected keys and Sunday logic."""
    context = generate_ai_context()
    summary = context["rules_summary"]
    assert "odd_week_pattern" in summary
    assert "even_week_pattern" in summary
    assert "special_sunday_rule" in summary
    assert "modulo_support" in summary
    # Check Sunday modulo mention
    assert "CW mod 4" in summary["special_sunday_rule"]


def test_handoff_rules_content():
    """Verify handoff rules summary."""
    context = generate_ai_context()
    handoff = context["handoff_rules"]
    assert "default_handoff" in handoff
    assert handoff["default_handoff"] == "Default handoff location: school"


def test_json_schema_structure():
    """Verify schema has required properties."""
    schema = _generate_json_schema()
    assert schema["$schema"].startswith("http://json-schema.org")
    assert "properties" in schema
    assert "parties" in schema["properties"]
    assert "rules" in schema["properties"]


def test_ai_instructions_structure():
    """Verify instructions have expected sections."""
    instructions = _generate_ai_instructions()
    assert "understanding_schedule" in instructions
    assert isinstance(instructions["understanding_schedule"], list)
    assert "making_decisions" in instructions
    assert "drafting_messages" in instructions


def test_generate_ai_context_examples_summary():
    """Verify week summaries in examples."""
    context = generate_ai_context(weeks_ahead=1)
    examples = context["resolved_examples"]
    week = examples[0]
    assert "summary" in week
    assert "Full week" in week["summary"] or "days" in week["summary"]


def test_export_ai_context_no_config():
    """Test export without config (uses default)."""
    result = export_ai_context()
    data = json.loads(result)
    assert "system_description" in data


def test_export_ai_context_with_output(tmp_path):
    """Test export to file."""
    out_path = tmp_path / "context.json"
    result = export_ai_context(output_path=str(out_path))
    assert "exported to" in result
    assert out_path.exists()
    assert out_path.read_text()
    out_path.unlink()


def test_export_ai_context_custom_params():
    """Test export with config path, date, weeks."""
    # Use schema/example as config (assuming exists, or skip)
    result = export_ai_context(
        config_path=str(Path(__file__).parent.parent / "schema/example-schedule.generic.json"),
        target_date="2025-02-03",
        weeks_ahead=2,
    )
    data = json.loads(result)
    assert data["current_date"] == "2025-02-03"
    assert len(data["resolved_examples"]) == 2
