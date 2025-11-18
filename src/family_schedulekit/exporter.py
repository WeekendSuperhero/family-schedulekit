from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Literal

from .models import ScheduleConfigModel, Weekday
from .resolver import resolve_for_date

type DayRecord = dict[str, object]
type ExportFormat = Literal["csv", "json", "jsonl", "ics", "md", "png"]


@dataclass(slots=True)
class ExportPlan:
    start: date
    weeks: int
    outdir: Path
    formats: tuple[ExportFormat, ...] = (
        "csv",
        "json",
        "jsonl",
        "ics",
        "md",
    )


def _daterange(start: date, days: int) -> Iterable[date]:
    for i in range(days):
        yield start + timedelta(days=i)


def resolve_range(start: date, weeks: int, cfg: ScheduleConfigModel) -> list[DayRecord]:
    days = weeks * 7
    out: list[DayRecord] = []
    for d in _daterange(start, days):
        rec = resolve_for_date(d, cfg)
        rec["weekday"] = Weekday.from_python_weekday(d.weekday()).value
        rec["iso_date"] = d.isoformat()
        rec["calendar_week_system"] = cfg.calendar_week_system

        # Add custom swap color if specified in config
        if rec.get("is_swap") and d.isoformat() in cfg.swaps:
            swap = cfg.swaps[d.isoformat()]
            if swap.color:
                rec["swap_color"] = swap.color

        out.append(rec)
    return out


def _csv_lines(records: list[DayRecord]) -> list[str]:
    header = ["iso_date", "weekday", "calendar_week", "guardian", "handoff"]
    lines = [",".join(header)]
    for r in records:
        row = [
            str(r["date"]),
            str(r["weekday"]),
            str(r["calendar_week"]),
            str(r["guardian"]),
            "" if r["handoff"] is None else str(r["handoff"]),
        ]
        # basic CSV escape
        row = [('"' + c.replace('"', '""') + '"') if ("," in c or " " in c) else c for c in row]
        lines.append(",".join(row))
    return lines


def _mk_uid(prefix: str, dt: date) -> str:
    # RFC5545-ish unique id
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{dt.isoformat()}-{ts}@family-schedulekit"


def _ical_for_records(records: list[DayRecord]) -> str:
    # All-day events (midnight to midnight). Sunday Dad->Mom handoff at 13:00 note.
    # No timezone complexity; all-day events use DATE values.
    lines = [
        "BEGIN:VCALENDAR",
        "PRODID:-//family-schedulekit//EN",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    for r in records:
        d = date.fromisoformat(r["date"])  # type: ignore[arg-type]
        start = d.strftime("%Y%m%d")
        end = (d + timedelta(days=1)).strftime("%Y%m%d")
        summary = f"{str(r['weekday']).capitalize()}: {str(r['guardian']).capitalize()}"
        desc = f"ISO week {r['calendar_week']} ({r['calendar_week_system']})"
        if r.get("handoff") == "after_school":
            desc += "\\nHandoff: after school (Friday)."
        elif r.get("handoff") == "dad_to_mom_by_1pm":
            desc += "\\nHandoff: Dad → Mom by 1 PM (Sunday)."
        uid = _mk_uid("day", d)
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART;VALUE=DATE:{start}",
                f"DTEND;VALUE=DATE:{end}",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{desc}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\n".join(lines)


# ---------- Prompt generation (JSONL) ----------


def _swap_messages_for_records(records: list[DayRecord]) -> list[dict[str, str]]:
    """
    Generate AI-friendly message pairs for likely communications.
    Format: {"input": "...", "ideal": "..."} JSONL-ready.
    """
    out: list[dict[str, str]] = []

    for r in records:
        day = Weekday(str(r["weekday"]))
        date_str = str(r["date"])  # ISO string from resolve_for_date

        # Weekday school handoff reminders (Mon-Thu)
        if day in (Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY, Weekday.THURSDAY):
            who = str(r["guardian"])
            out.append(
                {
                    "input": f"Draft a short reminder that {who} has the kids on {day.value} {date_str} with handoff at school.",
                    "ideal": f"Quick reminder: {who.capitalize()} has the kids on {day.value.capitalize()} ({date_str}). Handoff at school. Thanks!",
                }
            )

        # Friday after school start of weekend
        if day is Weekday.FRIDAY and r.get("handoff") == "after_school":
            who = str(r["guardian"])
            out.append(
                {
                    "input": f"Draft a message to confirm weekend start on Friday {date_str} after school; {who} is picking up.",
                    "ideal": f"Confirming: {who.capitalize()} starts the weekend on Friday ({date_str}) after school pickup.",
                }
            )

        # Sunday exception messaging
        if day is Weekday.SUNDAY:
            who = str(r["guardian"])
            if r.get("handoff") == "dad_to_mom_by_1pm":
                out.append(
                    {
                        "input": f"Draft a polite note for Sunday {date_str} confirming drop-off from Dad to Mom by 1 PM.",
                        "ideal": f"Hi! Confirming Sunday ({date_str}) drop-off: Dad → Mom by 1:00 PM. See you then.",
                    }
                )
            else:
                out.append(
                    {
                        "input": f"Draft a brief message that {who} has the kids all day on Sunday {date_str}.",
                        "ideal": f"Just a heads up: {who.capitalize()} has the kids all day Sunday ({date_str}).",
                    }
                )

    return out


# ---------- Writers ----------


def write_exports(plan: ExportPlan, cfg: ScheduleConfigModel, start_weekday_override: str | None = None) -> dict[str, Path]:
    plan.outdir.mkdir(parents=True, exist_ok=True)
    records = resolve_range(plan.start, plan.weeks, cfg)
    paths: dict[str, Path] = {}

    if "csv" in plan.formats:
        p = plan.outdir / f"schedule_{plan.start.isoformat()}_{plan.weeks}w.csv"
        p.write_text("\n".join(_csv_lines(records)), encoding="utf-8")
        paths["csv"] = p

    if "json" in plan.formats:
        p = plan.outdir / f"schedule_{plan.start.isoformat()}_{plan.weeks}w.json"
        p.write_text(json.dumps(records, indent=2), encoding="utf-8")
        paths["json"] = p

    if "jsonl" in plan.formats:
        p = plan.outdir / f"messages_{plan.start.isoformat()}_{plan.weeks}w.jsonl"
        msgs = _swap_messages_for_records(records)
        with p.open("w", encoding="utf-8") as f:
            for m in msgs:
                f.write(json.dumps(m, ensure_ascii=False) + "\n")
        paths["jsonl"] = p

    if "ics" in plan.formats:
        p = plan.outdir / f"calendar_{plan.start.isoformat()}_{plan.weeks}w.ics"
        p.write_text(_ical_for_records(records), encoding="utf-8")
        paths["ics"] = p

    if "md" in plan.formats:
        p = plan.outdir / f"summary_{plan.start.isoformat()}_{plan.weeks}w.md"
        md = [
            "# Family Schedule Summary",
            f"- Range start: **{plan.start.isoformat()}**",
            f"- Weeks: **{plan.weeks}**",
            "- ISO 8601 calendar weeks included.",
            "",
            "| Date | Weekday | CW | Guardian | Handoff |",
            "|---|---:|---:|---|---|",
        ]
        for r in records:
            handoff_str = "" if r["handoff"] is None else str(r["handoff"])
            md.append(f"| {r['date']} | {str(r['weekday']).capitalize()} | {r['calendar_week']} | {str(r['guardian']).capitalize()} | {handoff_str} |")
        p.write_text("\n".join(md), encoding="utf-8")
        paths["md"] = p

    if "png" in plan.formats:
        png_path = plan.outdir / f"visual_{plan.start.isoformat()}_{plan.weeks}w.png"
        from .visualizer import render_schedule_image

        # Convert config visualization palette to dict for render_schedule_image
        palette: dict[str, str | tuple[int, int, int] | int] = {
            "mom": cfg.visualization.mom,
            "dad": cfg.visualization.dad,
            "swap_shade_percent": cfg.visualization.swap_shade_percent,
        }
        if cfg.visualization.holiday:
            palette["holiday"] = cfg.visualization.holiday
        if cfg.visualization.unknown:
            palette["unknown"] = cfg.visualization.unknown

        # Use CLI override if provided, otherwise use config setting
        start_weekday = start_weekday_override if start_weekday_override else cfg.visualization.start_weekday

        render_schedule_image(records, plan.start, plan.weeks, png_path, palette=palette, start_weekday=start_weekday)
        paths["png"] = png_path

    return paths
