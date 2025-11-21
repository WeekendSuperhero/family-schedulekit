from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

import yaml

try:  # pragma: no cover - optional dependency handled at runtime
    import argcomplete
except ImportError:  # pragma: no cover
    argcomplete = None  # type: ignore[assignment]

from .ai_helper import export_ai_context
from .colors import list_all_colors
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
        guardian_1=sp.guardian_1,
        guardian_2=sp.guardian_2,
        children=sp.child,
        template=sp.template,
        outfile=outfile,
        overwrite=sp.force,
    )
    out = write_config(params)
    print(f"Wrote schedule config → {out}")


def _map_guardian_to_name(guardian_key: str, cfg: ScheduleConfigModel) -> str:
    """Map guardian_1/guardian_2 to actual names from config."""
    if guardian_key == "guardian_1":
        return cfg.parties.guardian_1
    elif guardian_key == "guardian_2":
        return cfg.parties.guardian_2
    return guardian_key


def _cmd_resolve(sp):
    cfg = _load_config(sp.config)
    if sp.week_of:
        # If --week-of is specified with a value, use it; otherwise default to current week
        if sp.week_of == "current":
            anchor = _get_most_recent_monday()
        else:
            anchor = datetime.strptime(sp.week_of, "%Y-%m-%d").date()
        week = resolve_week_of(anchor, cfg)
        # Map guardian keys to actual names
        resolved_schedule = {}
        for k, v in week.items():
            resolved_schedule[k] = {"guardian": _map_guardian_to_name(str(v["guardian"]), cfg), "handoff": v["handoff"]}
        print(
            json.dumps(
                {
                    "calendar_week": iso_week(anchor),
                    "calendar_week_system": cfg.calendar_week_system,
                    "resolved_schedule": resolved_schedule,
                },
                indent=2,
            )
        )
    else:
        # Default to current week if no date provided
        if not sp.date:
            anchor = _get_most_recent_monday()
            week = resolve_week_of(anchor, cfg)
            # Map guardian keys to actual names
            resolved_schedule = {}
            for k, v in week.items():
                resolved_schedule[k] = {"guardian": _map_guardian_to_name(str(v["guardian"]), cfg), "handoff": v["handoff"]}
            print(
                json.dumps(
                    {
                        "calendar_week": iso_week(anchor),
                        "calendar_week_system": cfg.calendar_week_system,
                        "resolved_schedule": resolved_schedule,
                    },
                    indent=2,
                )
            )
        else:
            target = datetime.strptime(sp.date, "%Y-%m-%d").date()
            result = resolve_for_date(target, cfg)
            guardian = result["guardian"]
            # Map guardian key to actual name
            result["guardian"] = _map_guardian_to_name(str(guardian), cfg)
            print(json.dumps(result, indent=2))


def _cmd_list(sp):
    print("Available templates:")
    for t in list_templates():
        print("  -", t)


def _cmd_list_colors(sp):
    list_all_colors()


def _cmd_convert(sp):
    """Convert a config file from JSON to YAML or vice versa."""
    input_path = Path(sp.input)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    # Determine output path
    if sp.output:
        output_path = Path(sp.output)
    else:
        # Auto-determine output filename based on conversion direction
        if input_path.suffix == ".json":
            output_path = input_path.with_suffix(".yaml")
        else:
            output_path = input_path.with_suffix(".json")

    # Check if output exists
    if output_path.exists() and not sp.force:
        raise SystemExit(f"Output file already exists: {output_path}\nUse -f/--force to overwrite")

    # Load config
    content = input_path.read_text()
    if input_path.suffix in (".yaml", ".yml"):
        data = yaml.safe_load(content)
        cfg = ScheduleConfigModel.model_validate(data)
    else:
        cfg = ScheduleConfigModel.model_validate_json(content)

    # Write in new format
    data = cfg.model_dump(mode="json")
    if output_path.suffix in (".yaml", ".yml"):
        output_content = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True, width=120, indent=2)
    else:
        output_content = json.dumps(data, indent=2)

    output_path.write_text(output_content, encoding="utf-8")
    print(f"Converted {input_path} → {output_path}")


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

    Supports both YAML (.yaml, .yml) and JSON (.json) formats.

    Priority:
    1. Specified config path (if provided and exists)
    2. Default user config (~/.config/family-schedulekit/schedule.yaml or schedule.json)
    3. Packaged example config
    """

    def _load_config_file(path: Path) -> ScheduleConfigModel:
        """Load config from file, detecting format by extension."""
        content = path.read_text()
        if path.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(content)
            return ScheduleConfigModel.model_validate(data)
        else:
            return ScheduleConfigModel.model_validate_json(content)

    if config_arg:
        cfg_path = Path(config_arg)
        if cfg_path.exists():
            return _load_config_file(cfg_path)

    # Try default user config location
    if config_exists():
        default_path = get_config_path()
        return _load_config_file(default_path)

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

    # Pass the start_weekday override if provided
    start_weekday_override = sp.start_weekday if hasattr(sp, "start_weekday") else None
    paths = write_exports(plan, cfg, start_weekday_override=start_weekday_override)
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
    ap_init.add_argument("--guardian-1", dest="guardian_1", required=True)
    ap_init.add_argument("--guardian-2", dest="guardian_2", required=True)
    ap_init.add_argument("--child", action="append", default=[])
    ap_init.add_argument("--template", default="generic", choices=["generic"])
    ap_init.add_argument("-o", "--outfile", default=None, help="Output file (default: ~/.config/family-schedulekit/schedule.json)")
    ap_init.add_argument("-f", "--force", action="store_true")
    ap_init.set_defaults(func=_cmd_init)

    ap_res = sub.add_parser("resolve", help="Resolve a date or week (defaults to current week)")
    ap_res.add_argument("date", nargs="?", help="Date in YYYY-MM-DD format (optional, defaults to current week)")
    ap_res.add_argument("--week-of", nargs="?", const="current", help="Show full week starting from date (or 'current' for this week)")
    ap_res.add_argument("--config", default=None, help="Config file (default: ~/.config/family-schedulekit/schedule.json or example)")
    ap_res.set_defaults(func=_cmd_resolve)

    ap_list = sub.add_parser("list-templates", help="Show available templates")
    ap_list.set_defaults(func=_cmd_list)

    ap_colors = sub.add_parser("list-colors", help="Show all available CSS3 color names with terminal preview")
    ap_colors.set_defaults(func=_cmd_list_colors)

    ap_convert = sub.add_parser("convert", help="Convert config file between JSON and YAML formats")
    ap_convert.add_argument("input", help="Input config file (.json, .yaml, or .yml)")
    ap_convert.add_argument("-o", "--output", help="Output file (default: auto-detect based on input)")
    ap_convert.add_argument("-f", "--force", action="store_true", help="Overwrite output file if it exists")
    ap_convert.set_defaults(func=_cmd_convert)

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
    ap_exp.add_argument(
        "--start-weekday",
        choices=["monday", "sunday"],
        default=None,
        help="First day of week for PNG calendar (default: from config, or monday)",
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
