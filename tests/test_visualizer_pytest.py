from datetime import date

from family_schedulekit import load_default_config, render_schedule_image
from family_schedulekit.exporter import ExportPlan, resolve_range, write_exports


def test_render_schedule_image(tmp_path):
    cfg = load_default_config()
    start = date(2025, 2, 3)  # Monday
    records = resolve_range(start, 2, cfg)
    out = tmp_path / "schedule.png"

    render_schedule_image(records, start, 2, out)

    assert out.exists()
    assert out.stat().st_size > 0


def test_export_plan_png(tmp_path):
    cfg = load_default_config()
    plan = ExportPlan(start=date(2025, 2, 3), weeks=1, outdir=tmp_path, formats=("png",))

    paths = write_exports(plan, cfg)

    assert "png" in paths
    assert paths["png"].exists()
