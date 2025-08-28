from __future__ import annotations
import argparse, json
from pathlib import Path
from datetime import datetime

from .models import ScheduleConfigModel
from .resolver import iso_week, resolve_for_date, resolve_week_of
from .generator import InitParams, write_config
from .resources import load_default_config, list_templates
from .exporter import ExportPlan, write_exports
from .ai_helper import export_ai_context

def _cmd_init(sp):
    params = InitParams(
        mom=sp.mom, dad=sp.dad, children=sp.child,
        template=sp.template, outfile=Path(sp.outfile), overwrite=sp.force,
    )
    out = write_config(params)
    print(f"Wrote schedule config → {out}")

def _cmd_resolve(sp):
    cfg_path = Path(sp.config)
    cfg = ScheduleConfigModel.model_validate_json(cfg_path.read_text()) if cfg_path.exists() else load_default_config()
    if sp.week_of:
        anchor = datetime.strptime(sp.week_of, "%Y-%m-%d").date()
        week = resolve_week_of(anchor, cfg)
        print(json.dumps({
            "calendar_week": iso_week(anchor),
            "calendar_week_system": cfg.calendar_week_system,
            "resolved_schedule": {k: {"guardian": v["guardian"], "handoff": v["handoff"]} for k, v in week.items()}
        }, indent=2))
    else:
        if not sp.date:
            raise SystemExit("Provide a date (YYYY-MM-DD) or use --week-of")
        target = datetime.strptime(sp.date, "%Y-%m-%d").date()
        print(json.dumps(resolve_for_date(target, cfg), indent=2))

def _cmd_list(sp):
    print("Available templates:")
    for t in list_templates():
        print("  -", t)

def _cmd_export(sp):
    cfg_path = Path(sp.config)
    cfg = ScheduleConfigModel.model_validate_json(cfg_path.read_text()) if cfg_path.exists() else load_default_config()
    start = datetime.strptime(sp.start, "%Y-%m-%d").date()
    outdir = Path(sp.outdir)
    fmts = tuple({f.lower() for f in sp.formats})  # unique, normalized
    plan = ExportPlan(start=start, weeks=sp.weeks, outdir=outdir, formats=fmts)  # type: ignore[arg-type]
    paths = write_exports(plan, cfg)
    print("Exported:")
    for k, p in paths.items():
        print(f"  {k}: {p}")

def _cmd_ai_context(sp):
    result = export_ai_context(
        config_path=sp.config if Path(sp.config).exists() else None,
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
    ap_init.add_argument("-o","--outfile", default="schema/my-schedule.json")
    ap_init.add_argument("-f","--force", action="store_true")
    ap_init.set_defaults(func=_cmd_init)

    ap_res = sub.add_parser("resolve", help="Resolve a date or week")
    ap_res.add_argument("date", nargs="?")
    ap_res.add_argument("--week-of")
    ap_res.add_argument("--config", default="schema/example-schedule.json")
    ap_res.set_defaults(func=_cmd_resolve)

    ap_list = sub.add_parser("list-templates", help="Show available templates")
    ap_list.set_defaults(func=_cmd_list)

    ap_exp = sub.add_parser("export", help="Export AI-ready files over a date range")
    ap_exp.add_argument("--config", default="schema/example-schedule.json", help="Path to config (falls back to packaged default)")
    ap_exp.add_argument("--start", required=True, help="Start date YYYY-MM-DD (Monday recommended)")
    ap_exp.add_argument("--weeks", type=int, default=12, help="How many weeks to include (default 12)")
    ap_exp.add_argument("--outdir", default="out", help="Output directory (default: ./out)")
    ap_exp.add_argument("--formats", nargs="+", default=["csv","json","jsonl","ics","md"], help="One or more of: csv json jsonl ics md")
    ap_exp.set_defaults(func=_cmd_export)

    ap_ai = sub.add_parser("ai-context", help="Generate AI-friendly context with schema and examples")
    ap_ai.add_argument("--config", default="schema/example-schedule.json", help="Path to schedule config")
    ap_ai.add_argument("--date", help="Target date YYYY-MM-DD (default: today)")
    ap_ai.add_argument("--weeks", type=int, default=4, help="Weeks of examples to generate")
    ap_ai.add_argument("--output", help="Output file path (if not specified, prints to stdout)")
    ap_ai.set_defaults(func=_cmd_ai_context)

    args = ap.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
