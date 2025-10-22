from __future__ import annotations
from datetime import date, timedelta
from .models import Guardian, ScheduleConfigModel, Weekday


def iso_week(dt: date) -> int:
    return dt.isocalendar().week


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
            handoff = cfg.handoff.weekdays
        case Weekday.FRIDAY:
            if cw % 2 == 1:
                guardian = cfg.rules.weekends.odd_weeks.friday
            else:
                guardian = cfg.rules.weekends.even_weeks.friday
            handoff = "after_school"
        case Weekday.SATURDAY:
            guardian = cfg.rules.weekends.odd_weeks.saturday if cw % 2 == 1 else cfg.rules.weekends.even_weeks.saturday
        case Weekday.SUNDAY:
            if cw % 2 == 1:
                guardian = cfg.rules.weekends.odd_weeks.sunday
            else:
                sunday_rule = cfg.rules.weekends.even_weeks.sunday
                guardian = sunday_rule.cw_mod4_equals_0 if (cw % 4 == 0) else sunday_rule.otherwise
                if guardian == "dad" and cfg.handoff.sunday_dad_to_mom == "by_1pm":
                    handoff = "dad_to_mom_by_1pm"
        case _:
            raise AssertionError(f"Unhandled weekday: {day!r}")

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
