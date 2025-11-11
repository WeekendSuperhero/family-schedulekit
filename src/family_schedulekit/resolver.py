from __future__ import annotations

from datetime import date, timedelta

from .models import Guardian, ScheduleConfigModel, Weekday, WeekdayHandoffs, WeekdayRule


def iso_week(dt: date) -> int:
    return dt.isocalendar().week


def _get_weekday_handoff(cfg: ScheduleConfigModel) -> str:
    """Get the weekday handoff location/description."""
    if isinstance(cfg.handoff.weekdays, str):
        return cfg.handoff.weekdays
    return cfg.handoff.weekdays.location


def resolve_weekday_rule(rule: Guardian | WeekdayRule, cw: int) -> Guardian:
    """Resolve a weekday rule to a guardian based on calendar week.

    Args:
        rule: Either a direct guardian assignment or a WeekdayRule with modulo conditions
        cw: Calendar week number

    Returns:
        The guardian for this calendar week
    """
    if isinstance(rule, str):
        return rule

    # Check modulo rules in order
    for modulo_rule in rule.modulo_rules:
        if cw % modulo_rule.modulo == modulo_rule.remainder:
            return modulo_rule.guardian

    # No modulo rules matched, use otherwise
    return rule.otherwise


def resolve_for_date(dt: date, cfg: ScheduleConfigModel) -> dict[str, object]:
    iso_date = dt.isoformat()
    cw = iso_week(dt)
    day = Weekday.from_python_weekday(dt.weekday())
    handoff: str | None = None

    if iso_date in cfg.holidays:
        return {
            "date": iso_date,
            "calendar_week": cw,
            "guardian": cfg.holidays[iso_date],
            "handoff": None,
        }

    guardian: Guardian
    match day:
        case Weekday.MONDAY | Weekday.TUESDAY | Weekday.WEDNESDAY | Weekday.THURSDAY:
            guardian = getattr(cfg.rules.weekdays, day.value)
            handoff = _get_weekday_handoff(cfg)
        case Weekday.FRIDAY:
            if cw % 2 == 1:
                guardian = cfg.rules.weekends.odd_weeks.friday
            else:
                guardian = resolve_weekday_rule(cfg.rules.weekends.even_weeks.friday, cw)
            handoff = "after_school"
        case Weekday.SATURDAY:
            if cw % 2 == 1:
                guardian = cfg.rules.weekends.odd_weeks.saturday
            else:
                guardian = resolve_weekday_rule(cfg.rules.weekends.even_weeks.saturday, cw)
        case Weekday.SUNDAY:
            if cw % 2 == 1:
                guardian = cfg.rules.weekends.odd_weeks.sunday
            else:
                guardian = resolve_weekday_rule(cfg.rules.weekends.even_weeks.sunday, cw)
        case _:
            raise AssertionError(f"Unhandled weekday: {day!r}")

    # Apply special handoff rules if configured for this weekday
    if day in cfg.handoff.special_handoffs:
        special = cfg.handoff.special_handoffs[day]
        # Only apply if the current guardian matches the "from" guardian
        if guardian == special.from_guardian:
            if special.description:
                handoff = special.description
            else:
                # Auto-generate description
                time_str = special.time.format()
                handoff = f"{special.from_guardian}_to_{special.to_guardian}_{time_str}"

    return {"date": iso_date, "calendar_week": cw, "guardian": guardian, "handoff": handoff}


def resolve_week_of(anchor: date, cfg: ScheduleConfigModel) -> dict[str, dict[str, object]]:
    monday = anchor - timedelta(days=anchor.weekday())
    out: dict[str, dict[str, object]] = {}
    for offset in range(7):
        current = monday + timedelta(days=offset)
        res = resolve_for_date(current, cfg)
        weekday = Weekday.from_python_weekday(current.weekday())
        out[weekday.value] = res
    return out
