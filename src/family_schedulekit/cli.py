from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

try:  # pragma: no cover - optional dependency handled at runtime
    import argcomplete
except ImportError:  # pragma: no cover
    argcomplete = None  # type: ignore[assignment]

from .ai_helper import export_ai_context
from .config import config_exists, ensure_config_dir, get_config_path
from .exporter import ExportPlan, write_exports
from .generator import InitParams, write_config
from .models import ScheduleConfigModel
from .resolver import iso_week, resolve_for_date, resolve_week_of
from .resources import list_templates, load_default_config


def _cmd_init(sp):
    # Use default config location if no outfile specified
    if sp.outfile is None:
        ensure_config_dir()
        outfile = get_config_path()
    else:
        outfile = Path(sp.outfile)

    params = InitParams(
        mom=sp.mom,
        dad=sp.dad,
        children=sp.child,
        template=sp.template,
        outfile=outfile,
        overwrite=sp.force,
    )
    out = write_config(params)
    print(f"Wrote schedule config → {out}")


def _cmd_resolve(sp):
    cfg = _load_config(sp.config)
    if sp.week_of:
        anchor = datetime.strptime(sp.week_of, "%Y-%m-%d").date()
        week = resolve_week_of(anchor, cfg)
        print(
            json.dumps(
                {
                    "calendar_week": iso_week(anchor),
                    "calendar_week_system": cfg.calendar_week_system,
                    "resolved_schedule": {k: {"guardian": v["guardian"], "handoff": v["handoff"]} for k, v in week.items()},
                },
                indent=2,
            )
        )
    else:
        if not sp.date:
            raise SystemExit("Provide a date (YYYY-MM-DD) or use --week-of")
        target = datetime.strptime(sp.date, "%Y-%m-%d").date()
        print(json.dumps(resolve_for_date(target, cfg), indent=2))


def _cmd_list(sp):
    print("Available templates:")
    for t in list_templates():
        print("  -", t)


def _get_most_recent_monday():
    """Get the most recent Monday (including today if today is Monday)."""
    today = datetime.now().date()
    # Monday is 0, Sunday is 6
    days_since_monday = today.weekday()
    most_recent_monday = today - timedelta(days=days_since_monday)
    return most_recent_monday


def _load_config(config_arg: str | None) -> ScheduleConfigModel:
    """
    Load config from specified path, default location, or packaged example.

    Priority:
    1. Specified config path (if provided and exists)
    2. Default user config (~/.config/family-schedulekit/schedule.json)
    3. Packaged example config
    """
    if config_arg:
        cfg_path = Path(config_arg)
        if cfg_path.exists():
            return ScheduleConfigModel.model_validate_json(cfg_path.read_text())

    # Try default user config location
    if config_exists():
        default_path = get_config_path()
        return ScheduleConfigModel.model_validate_json(default_path.read_text())

    # Fall back to packaged default
    return load_default_config()


def _cmd_export(sp):
    cfg = _load_config(sp.config)

    # Default to most recent Monday if no start date provided
    if sp.start:
        start = datetime.strptime(sp.start, "%Y-%m-%d").date()
    else:
        start = _get_most_recent_monday()

    outdir = Path(sp.outdir)
    fmts = tuple({f.lower() for f in sp.formats})  # unique, normalized
    plan = ExportPlan(start=start, weeks=sp.weeks, outdir=outdir, formats=fmts)
    paths = write_exports(plan, cfg)
    print("Exported:")
    for k, p in paths.items():
        print(f"  {k}: {p}")


def _cmd_ai_context(sp):
    # Determine which config to use
    config_path = None
    if sp.config:
        cfg_path = Path(sp.config)
        if cfg_path.exists():
            config_path = sp.config
    elif config_exists():
        config_path = str(get_config_path())

    result = export_ai_context(
        config_path=config_path,
        output_path=sp.output,
        target_date=sp.date,
        weeks_ahead=sp.weeks,
    )
    if sp.output:
        print(result)
    else:
        print(result)


def main():
    ap = argparse.ArgumentParser(description="family-schedulekit CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ap_init = sub.add_parser("init", help="Generate a new schedule config")
    ap_init.add_argument("--mom", required=True)
    ap_init.add_argument("--dad", required=True)
    ap_init.add_argument("--child", action="append", default=[])
    ap_init.add_argument("--template", default="generic", choices=["generic"])
    ap_init.add_argument("-o", "--outfile", default=None, help="Output file (default: ~/.config/family-schedulekit/schedule.json)")
    ap_init.add_argument("-f", "--force", action="store_true")
    ap_init.set_defaults(func=_cmd_init)

    ap_res = sub.add_parser("resolve", help="Resolve a date or week")
    ap_res.add_argument("date", nargs="?")
    ap_res.add_argument("--week-of")
    ap_res.add_argument("--config", default=None, help="Config file (default: ~/.config/family-schedulekit/schedule.json or example)")
    ap_res.set_defaults(func=_cmd_resolve)

    ap_list = sub.add_parser("list-templates", help="Show available templates")
    ap_list.set_defaults(func=_cmd_list)

    ap_exp = sub.add_parser("export", help="Export AI-ready files over a date range")
    ap_exp.add_argument(
        "--config",
        default=None,
        help="Config file (default: ~/.config/family-schedulekit/schedule.json or example)",
    )
    ap_exp.add_argument("--start", help="Start date YYYY-MM-DD (default: most recent Monday)")
    ap_exp.add_argument("--weeks", type=int, default=12, help="How many weeks to include (default 12)")
    ap_exp.add_argument("--outdir", default="out", help="Output directory (default: ./out)")
    ap_exp.add_argument(
        "--formats",
        nargs="+",
        default=["csv", "json", "jsonl", "ics", "md"],
        help="One or more of: csv json jsonl ics md png",
    )
    ap_exp.set_defaults(func=_cmd_export)

    ap_ai = sub.add_parser("ai-context", help="Generate AI-friendly context with schema and examples")
    ap_ai.add_argument("--config", default=None, help="Config file (default: ~/.config/family-schedulekit/schedule.json or example)")
    ap_ai.add_argument("--date", help="Target date YYYY-MM-DD (default: today)")
    ap_ai.add_argument("--weeks", type=int, default=4, help="Weeks of examples to generate")
    ap_ai.add_argument("--output", help="Output file path (if not specified, prints to stdout)")
    ap_ai.set_defaults(func=_cmd_ai_context)

    if argcomplete is not None:
        argcomplete.autocomplete(ap)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
