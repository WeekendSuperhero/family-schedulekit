from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .models import ScheduleConfigModel
from .resolver import iso_week, resolve_for_date, resolve_week_of
from .resources import load_default_config


def generate_ai_context(
    config: ScheduleConfigModel | None = None,
    target_date: date | None = None,
    weeks_ahead: int = 4,
    include_examples: bool = True,
    include_schema: bool = True,
) -> dict[str, Any]:
    """
    Generate comprehensive context for AI to understand and work with the custody schedule.

    Args:
        config: Schedule configuration (defaults to generic template)
        target_date: Starting date for examples (defaults to today)
        weeks_ahead: How many weeks of examples to generate
        include_examples: Whether to include resolved schedule examples
        include_schema: Whether to include the JSON schema

    Returns:
        Dictionary with AI-friendly context including schema, rules, and examples
    """
    cfg = config or load_default_config()
    start_date = target_date or date.today()

    context: dict[str, Any] = {
        "system_description": (
            "This is a co-parenting schedule system using ISO 8601 week numbering. "
            "The schedule determines which guardian has custody on any given day, "
            "with special rules based on odd/even weeks and handoff logistics."
        ),
        "current_date": start_date.isoformat(),
        "current_week": iso_week(start_date),
        "parties": {
            "guardian_1": cfg.parties.guardian_1,
            "guardian_2": cfg.parties.guardian_2,
            "children": cfg.parties.children,
        },
        "rules_summary": _generate_rules_summary(cfg),
        "handoff_rules": _generate_handoff_rules(cfg),
    }

    if include_schema:
        context["json_schema"] = _generate_json_schema()
        context["configuration"] = json.loads(cfg.model_dump_json())

    if include_examples:
        context["resolved_examples"] = _generate_schedule_examples(cfg, start_date, weeks_ahead)
        context["decision_examples"] = _generate_decision_examples(cfg, start_date)

    context["ai_instructions"] = _generate_ai_instructions()

    return context


def _generate_rules_summary(cfg: ScheduleConfigModel) -> dict[str, str]:
    """Generate human-readable rules summary."""
    from .models import WeekdayRule

    # Describe even week Sunday rule
    sunday_rule = cfg.rules.even_weeks.sunday
    if isinstance(sunday_rule, WeekdayRule) and sunday_rule.modulo_rules:
        # Find the common mod 4 pattern
        mod4_rule = next((r for r in sunday_rule.modulo_rules if r.modulo == 4 and r.remainder == 0), None)
        if mod4_rule:
            sunday_desc = f"Sunday varies (CW%4==0: {mod4_rule.guardian} until 1pm, else: {sunday_rule.otherwise})"
            special_sunday = f"On even weeks where CW mod 4 equals 0 (CW4, CW8, CW12...), {mod4_rule.guardian} has Sunday but must return children by 1 PM"
        else:
            sunday_desc = "Sunday uses custom modulo rules"
            special_sunday = "Custom modulo rules apply to even-week Sundays"
    else:
        sunday_desc = f"Sunday: {sunday_rule}"
        special_sunday = "No special Sunday rules"

    return {
        "odd_week_pattern": f"Odd weeks (CW1, CW3, CW5...): All 7 days follow the odd week schedule",
        "even_week_pattern": f"Even weeks (CW2, CW4, CW6...): All 7 days follow the even week schedule, {sunday_desc}",
        "special_sunday_rule": special_sunday,
        "modulo_support": "Any day in odd or even weeks can use flexible modulo rules for complex rotation patterns",
    }


def _generate_handoff_rules(cfg: ScheduleConfigModel) -> dict[str, str]:
    """Generate handoff logistics rules."""
    return {
        "default_handoff": f"Default handoff location: {cfg.handoff.default_location}",
        "custody_changes": "Handoffs occur automatically when custody changes between guardians",
        "special_handoffs": "Special handoff rules can be configured for specific weekdays with custom times",
    }


def _generate_schedule_examples(cfg: ScheduleConfigModel, start: date, weeks: int) -> list[dict[str, Any]]:
    """Generate resolved schedule examples for multiple weeks."""
    examples: list[dict[str, Any]] = []
    current = start - timedelta(days=start.weekday())  # Start from Monday

    for week_num in range(weeks):
        week_start = current + timedelta(weeks=week_num)
        cw = iso_week(week_start)
        week_schedule = resolve_week_of(week_start, cfg)

        week_summary = {
            "week_start": week_start.isoformat(),
            "calendar_week": cw,
            "week_type": "odd" if cw % 2 == 1 else "even",
            "sunday_special": cw % 4 == 0,
            "schedule": week_schedule,
            "summary": _summarize_week(week_schedule, cfg),
        }
        examples.append(week_summary)

    return examples


def _summarize_week(week_schedule: dict[str, dict[str, Any]], cfg: ScheduleConfigModel) -> str:
    """Create a human-readable week summary."""
    guardian_1_days = sum(1 for day in week_schedule.values() if day["guardian"] == "guardian_1")
    guardian_2_days = 7 - guardian_1_days

    if guardian_1_days == 7:
        return f"Full week with {cfg.parties.guardian_1}"
    elif guardian_2_days == 7:
        return f"Full week with {cfg.parties.guardian_2}"
    else:
        return f"{cfg.parties.guardian_1}: {guardian_1_days} days, {cfg.parties.guardian_2}: {guardian_2_days} days"


def _generate_decision_examples(cfg: ScheduleConfigModel, start: date) -> list[dict[str, Any]]:
    """Generate examples of how to make scheduling decisions."""
    examples: list[dict[str, Any]] = []

    # Example 1: Planning an event
    event_date = start + timedelta(days=14)
    resolution = resolve_for_date(event_date, cfg)
    guardian_name = cfg.parties.guardian_1 if resolution["guardian"] == "guardian_1" else cfg.parties.guardian_2
    examples.append(
        {
            "scenario": "Planning a birthday party",
            "date": event_date.isoformat(),
            "question": f"Who should organize a birthday party on {event_date.strftime('%B %d, %Y')}?",
            "answer": f"{guardian_name} has custody",
            "resolution": resolution,
        }
    )

    # Example 2: Vacation planning
    vacation_start = start + timedelta(days=30)
    vacation_week = resolve_week_of(vacation_start, cfg)
    examples.append(
        {
            "scenario": "Planning a week-long vacation",
            "week_start": vacation_start.isoformat(),
            "question": "How is custody split for a vacation week?",
            "answer": _summarize_week(vacation_week, cfg),
            "details": vacation_week,
        }
    )

    # Example 3: Special handoff day
    next_day = start + timedelta(days=7)
    resolution = resolve_for_date(next_day, cfg)
    examples.append(
        {
            "scenario": "Activity planning with handoff",
            "date": next_day.isoformat(),
            "question": "What custody arrangements exist for this day?",
            "answer": _get_day_answer(next_day, resolution, cfg),
            "resolution": resolution,
        }
    )

    return examples


def _get_day_answer(day: date, resolution: dict[str, Any], cfg: ScheduleConfigModel) -> str:
    """Generate answer about day activities."""
    cw = iso_week(day)
    guardian_name = cfg.parties.guardian_1 if resolution["guardian"] == "guardian_1" else cfg.parties.guardian_2

    if resolution.get("handoff"):
        return f"{guardian_name} has custody with handoff: {resolution['handoff']} (CW{cw})"
    else:
        return f"{guardian_name} has full custody (CW{cw})"


def _generate_json_schema() -> dict[str, Any]:
    """Generate JSON Schema for the schedule configuration."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["parties", "calendar_week_system", "handoff", "rules"],
        "properties": {
            "parties": {
                "type": "object",
                "required": ["guardian_1", "guardian_2", "children"],
                "properties": {
                    "guardian_1": {
                        "type": "string",
                        "description": "Name/identifier for first guardian",
                    },
                    "guardian_2": {
                        "type": "string",
                        "description": "Name/identifier for second guardian",
                    },
                    "children": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of children's names",
                    },
                },
            },
            "calendar_week_system": {
                "type": "string",
                "enum": ["ISO8601"],
                "description": "Calendar week numbering system",
            },
            "handoff": {
                "type": "object",
                "properties": {
                    "default_location": {
                        "type": "string",
                        "description": "Default handoff location when custody changes",
                    },
                    "special_handoffs": {
                        "type": "object",
                        "description": "Special handoff rules for specific weekdays",
                    },
                },
            },
            "rules": {
                "type": "object",
                "required": ["odd_weeks", "even_weeks"],
                "description": "Custody rules organized by odd and even calendar weeks",
                "properties": {
                    "odd_weeks": {
                        "type": "object",
                        "description": "Rules for all 7 days in odd weeks (CW1, CW3, CW5...)",
                    },
                    "even_weeks": {
                        "type": "object",
                        "description": "Rules for all 7 days in even weeks (CW2, CW4, CW6...), supports modulo rules",
                    },
                },
            },
            "holidays": {
                "type": "object",
                "additionalProperties": {"type": "string", "enum": ["guardian_1", "guardian_2"]},
                "description": "Override rules for specific dates (YYYY-MM-DD format, DEPRECATED: use swaps)",
            },
            "swaps": {
                "type": "object",
                "description": "Date swaps/exceptions with optional colors and notes",
            },
        },
    }


def _generate_ai_instructions() -> dict[str, Any]:
    """Generate instructions for AI to use the schedule."""
    return {
        "understanding_schedule": [
            "Use ISO 8601 week numbering (week starts Monday, CW1 contains first Thursday of year)",
            "Check if week number is odd (CW%2==1) or even (CW%2==0)",
            "Odd weeks and even weeks each define custody for all 7 days",
            "Any day can use modulo rules for complex patterns",
            "Always consider handoff logistics when planning activities",
        ],
        "making_decisions": [
            "Identify the date in question",
            "Calculate the ISO week number",
            "Determine if it's an odd or even week",
            "Look up the guardian for that specific day in the appropriate week rules",
            "Check for any swaps or holiday overrides",
            "Consider handoff times for activity planning",
        ],
        "drafting_messages": {
            "for_scheduling": "Include specific date, day of week, guardian with custody, and any handoff details",
            "for_conflicts": "Reference the specific rule that applies and the ISO week number",
            "for_planning": "Consider multi-day custody blocks for trips or extended activities",
        },
    }


def export_ai_context(
    config_path: str | None = None,
    output_path: str | None = None,
    target_date: str | None = None,
    weeks_ahead: int = 4,
) -> str:
    """
    Export AI context to a JSON file or return as string.

    Args:
        config_path: Path to schedule configuration file
        output_path: Where to save the AI context (if None, returns string)
        target_date: Starting date in YYYY-MM-DD format
        weeks_ahead: How many weeks of examples to include

    Returns:
        JSON string of the AI context
    """
    # Load configuration
    if config_path:
        cfg = ScheduleConfigModel.model_validate_json(Path(config_path).read_text())
    else:
        cfg = load_default_config()

    # Parse target date
    start = None
    if target_date:
        start = datetime.strptime(target_date, "%Y-%m-%d").date()

    # Generate context
    context = generate_ai_context(
        config=cfg,
        target_date=start,
        weeks_ahead=weeks_ahead,
        include_examples=True,
        include_schema=True,
    )

    # Export
    json_str = json.dumps(context, indent=2, default=str)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json_str, encoding="utf-8")
        return f"AI context exported to {output_path}"

    return json_str
