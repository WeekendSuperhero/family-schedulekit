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
            "The schedule determines which parent has custody on any given day, "
            "with special rules for weekends and handoff logistics."
        ),
        "current_date": start_date.isoformat(),
        "current_week": iso_week(start_date),
        "parties": {
            "primary_caregiver": cfg.parties.mom,
            "secondary_caregiver": cfg.parties.dad,
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
    sunday_rule = cfg.rules.weekends.even_weeks.sunday
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
        "weekday_pattern": (f"Monday: {cfg.parties.mom}, Tuesday: {cfg.parties.dad}, Wednesday: {cfg.parties.mom}, Thursday: {cfg.parties.dad}"),
        "weekend_odd_weeks": f"Odd ISO weeks (CW1, CW3, CW5...): Full weekend with {cfg.parties.mom}",
        "weekend_even_weeks": (f"Even ISO weeks (CW2, CW4, CW6...): Friday-Saturday patterns may use modulo rules, {sunday_desc}"),
        "special_sunday_rule": special_sunday,
        "modulo_support": "Even-week days (Friday, Saturday, Sunday) support flexible modulo rules for complex rotation patterns",
    }


def _generate_handoff_rules(cfg: ScheduleConfigModel) -> dict[str, str]:
    """Generate handoff logistics rules."""
    return {
        "weekday_handoffs": "Exchanges happen at school (drop-off by one parent, pick-up by the other)",
        "friday_handoffs": "After school pickup by the parent who has the weekend",
        "sunday_special": f"When {cfg.parties.dad} has Sunday (CW%4==0), handoff to {cfg.parties.mom} by 1 PM",
        "no_handoff_days": "Saturdays and most Sundays have no handoffs (continuous custody)",
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
    mom_days = sum(1 for day in week_schedule.values() if day["guardian"] == "mom")
    dad_days = 7 - mom_days

    if mom_days == 7:
        return f"Full week with {cfg.parties.mom}"
    elif dad_days == 7:
        return f"Full week with {cfg.parties.dad}"
    else:
        return f"{cfg.parties.mom}: {mom_days} days, {cfg.parties.dad}: {dad_days} days"


def _generate_decision_examples(cfg: ScheduleConfigModel, start: date) -> list[dict[str, Any]]:
    """Generate examples of how to make scheduling decisions."""
    examples: list[dict[str, Any]] = []

    # Example 1: Planning an event
    event_date = start + timedelta(days=14)
    resolution = resolve_for_date(event_date, cfg)
    examples.append(
        {
            "scenario": "Planning a birthday party",
            "date": event_date.isoformat(),
            "question": f"Who should organize a birthday party on {event_date.strftime('%B %d, %Y')}?",
            "answer": f"{cfg.parties.mom if resolution['guardian'] == 'mom' else cfg.parties.dad} has custody",
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

    # Example 3: Special Sunday
    next_sunday = start + timedelta(days=(6 - start.weekday()) % 7)
    if next_sunday == start:
        next_sunday += timedelta(days=7)

    sunday_resolution = resolve_for_date(next_sunday, cfg)
    examples.append(
        {
            "scenario": "Sunday activity planning",
            "date": next_sunday.isoformat(),
            "question": f"Can {cfg.parties.dad} plan an all-day Sunday activity?",
            "answer": _get_sunday_answer(next_sunday, sunday_resolution, cfg),
            "resolution": sunday_resolution,
        }
    )

    return examples


def _get_sunday_answer(sunday: date, resolution: dict[str, Any], cfg: ScheduleConfigModel) -> str:
    """Generate answer about Sunday activities."""
    cw = iso_week(sunday)
    if resolution["guardian"] == "mom":
        return f"No, {cfg.parties.mom} has custody all day (CW{cw})"
    elif resolution["handoff"] == "dad_to_mom_by_1pm":
        return f"Only morning activities - must return by 1 PM (CW{cw}, special Sunday)"
    else:
        return f"Yes, {cfg.parties.dad} has full custody (CW{cw})"


def _generate_json_schema() -> dict[str, Any]:
    """Generate JSON Schema for the schedule configuration."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["parties", "calendar_week_system", "handoff", "rules"],
        "properties": {
            "parties": {
                "type": "object",
                "required": ["mom", "dad", "children"],
                "properties": {
                    "mom": {
                        "type": "string",
                        "description": "Name/identifier for primary caregiver",
                    },
                    "dad": {
                        "type": "string",
                        "description": "Name/identifier for secondary caregiver",
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
                "required": ["weekdays", "sunday_dad_to_mom"],
                "properties": {
                    "weekdays": {
                        "type": "string",
                        "enum": ["school"],
                        "description": "Weekday handoff location",
                    },
                    "sunday_dad_to_mom": {
                        "type": "string",
                        "enum": ["by_1pm"],
                        "description": "Special Sunday handoff time",
                    },
                },
            },
            "rules": {
                "type": "object",
                "required": ["weekdays", "weekends"],
                "properties": {
                    "weekdays": {
                        "type": "object",
                        "required": ["monday", "tuesday", "wednesday", "thursday"],
                        "properties": {
                            "monday": {"type": "string", "enum": ["mom", "dad"]},
                            "tuesday": {"type": "string", "enum": ["mom", "dad"]},
                            "wednesday": {"type": "string", "enum": ["mom", "dad"]},
                            "thursday": {"type": "string", "enum": ["mom", "dad"]},
                        },
                    },
                    "weekends": {
                        "type": "object",
                        "required": ["odd_weeks", "even_weeks"],
                        "properties": {
                            "odd_weeks": {
                                "type": "object",
                                "required": ["friday", "saturday", "sunday"],
                                "properties": {
                                    "friday": {"type": "string", "enum": ["mom", "dad"]},
                                    "saturday": {"type": "string", "enum": ["mom", "dad"]},
                                    "sunday": {"type": "string", "enum": ["mom", "dad"]},
                                },
                            },
                            "even_weeks": {
                                "type": "object",
                                "required": ["friday", "saturday", "sunday"],
                                "properties": {
                                    "friday": {
                                        "oneOf": [
                                            {"type": "string", "enum": ["mom", "dad"]},
                                            {
                                                "type": "object",
                                                "required": ["modulo_rules", "otherwise"],
                                                "properties": {
                                                    "modulo_rules": {
                                                        "type": "array",
                                                        "items": {
                                                            "type": "object",
                                                            "required": ["modulo", "remainder", "guardian"],
                                                            "properties": {
                                                                "modulo": {"type": "integer", "minimum": 2},
                                                                "remainder": {"type": "integer", "minimum": 0},
                                                                "guardian": {"type": "string", "enum": ["mom", "dad"]},
                                                            },
                                                        },
                                                    },
                                                    "otherwise": {"type": "string", "enum": ["mom", "dad"]},
                                                },
                                            },
                                        ]
                                    },
                                    "saturday": {
                                        "oneOf": [
                                            {"type": "string", "enum": ["mom", "dad"]},
                                            {
                                                "type": "object",
                                                "required": ["modulo_rules", "otherwise"],
                                                "properties": {
                                                    "modulo_rules": {
                                                        "type": "array",
                                                        "items": {
                                                            "type": "object",
                                                            "required": ["modulo", "remainder", "guardian"],
                                                            "properties": {
                                                                "modulo": {"type": "integer", "minimum": 2},
                                                                "remainder": {"type": "integer", "minimum": 0},
                                                                "guardian": {"type": "string", "enum": ["mom", "dad"]},
                                                            },
                                                        },
                                                    },
                                                    "otherwise": {"type": "string", "enum": ["mom", "dad"]},
                                                },
                                            },
                                        ]
                                    },
                                    "sunday": {
                                        "oneOf": [
                                            {"type": "string", "enum": ["mom", "dad"]},
                                            {
                                                "type": "object",
                                                "required": ["modulo_rules", "otherwise"],
                                                "properties": {
                                                    "modulo_rules": {
                                                        "type": "array",
                                                        "items": {
                                                            "type": "object",
                                                            "required": ["modulo", "remainder", "guardian"],
                                                            "properties": {
                                                                "modulo": {"type": "integer", "minimum": 2},
                                                                "remainder": {"type": "integer", "minimum": 0},
                                                                "guardian": {"type": "string", "enum": ["mom", "dad"]},
                                                            },
                                                        },
                                                    },
                                                    "otherwise": {"type": "string", "enum": ["mom", "dad"]},
                                                },
                                            },
                                        ]
                                    },
                                },
                            },
                        },
                    },
                },
            },
            "holidays": {
                "type": "object",
                "additionalProperties": {"type": "string", "enum": ["mom", "dad"]},
                "description": "Override rules for specific dates (YYYY-MM-DD format)",
            },
        },
    }


def _generate_ai_instructions() -> dict[str, Any]:
    """Generate instructions for AI to use the schedule."""
    return {
        "understanding_schedule": [
            "Use ISO 8601 week numbering (week starts Monday, CW1 contains first Thursday of year)",
            "Check if week number is odd (CW%2==1) or even (CW%2==0)",
            "For even week Sundays, check if CW%4==0 for special handoff rule",
            "Always consider handoff logistics when planning activities",
        ],
        "making_decisions": [
            "Identify the date in question",
            "Calculate the ISO week number",
            "Apply weekday or weekend rules based on day of week",
            "Check for any holiday overrides",
            "Consider handoff times for activity planning",
        ],
        "drafting_messages": {
            "for_scheduling": "Include specific date, day of week, parent with custody, and any handoff details",
            "for_conflicts": "Reference the specific rule that applies and the ISO week number",
            "for_planning": "Consider multi-day custody blocks for trips or extended activities",
        },
        "common_patterns": {
            "mom_blocks": "Mom typically has Wed-Mon blocks on odd weeks (6 consecutive days)",
            "dad_blocks": "Dad typically has Tue-Thu-Fri-Sat blocks on even weeks (can be 4-5 days)",
            "sunday_special": "Every 4th even week (CW4, CW8, CW12...), Dad returns kids by 1 PM Sunday",
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
