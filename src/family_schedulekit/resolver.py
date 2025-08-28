from __future__ import annotations
from datetime import date, timedelta
from typing import Dict, Optional
from .models import ScheduleConfigModel, Weekday, Guardian

def iso_week(dt: date) -> int:
    return dt.isocalendar().week

def _weekday_slug(dt: date) -> str:
    return Weekday.from_python_weekday(dt.weekday()).slug()

def resolve_for_date(dt: date, cfg: ScheduleConfigModel) -> Dict[str, object]:
    iso_date = dt.isoformat()
    cw = iso_week(dt)
    day = _weekday_slug(dt)
    handoff: Optional[str] = None

    if iso_date in cfg.holidays:
        return {"date": iso_date, "calendar_week": cw, "guardian": cfg.holidays[iso_date], "handoff": None}

    if day in ("monday","tuesday","wednesday","thursday"):
        guardian: Guardian = getattr(cfg.rules.weekdays, day)
        handoff = cfg.handoff.weekdays
    else:
        if cw % 2 == 1:
            weekend = cfg.rules.weekends.odd_weeks
            guardian = getattr(weekend, day)  # type: ignore[assignment]
            if day == "friday":
                handoff = "after_school"
        else:
            weekend = cfg.rules.weekends.even_weeks
            if day in ("friday","saturday"):
                guardian = getattr(weekend, day)  # type: ignore[assignment]
                if day == "friday":
                    handoff = "after_school"
            else:
                sr = weekend.sunday
                guardian = sr.cw_mod4_equals_0 if (cw % 4 == 0) else sr.otherwise
                if guardian == "dad" and cfg.handoff.sunday_dad_to_mom == "by_1pm":
                    handoff = "dad_to_mom_by_1pm"

    return {"date": iso_date, "calendar_week": cw, "guardian": guardian, "handoff": handoff}

def resolve_week_of(anchor: date, cfg: ScheduleConfigModel) -> Dict[str, Dict[str, object]]:
    monday = anchor - timedelta(days=anchor.weekday())
    out: Dict[str, Dict[str, object]] = {}
    for i in range(7):
        d = monday + timedelta(days=i)
        res = resolve_for_date(d, cfg)
        out[_weekday_slug(d)] = res
    return out
