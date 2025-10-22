from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

try:  # pragma: no cover - exercised via optional dependency in tests
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - fallback evaluated at runtime
    Image = ImageDraw = ImageFont = None  # type: ignore[assignment]

DayRecord = Dict[str, object]

Palette = Dict[str, Tuple[int, int, int]]

_DEFAULT_PALETTE: Palette = {
    "mom": (242, 139, 130),  # soft red
    "dad": (129, 201, 149),  # soft green
    "holiday": (174, 203, 248),  # light blue override
    "unknown": (200, 200, 200),
}

_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _hex_to_rgb(value: str) -> Tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Invalid color value '{value}'. Use 6-character hex (e.g. #F28B82).")
    return tuple(int(value[i : i + 2], 16) for i in range(0, 6, 2))  # type: ignore[return-value]


def _normalize_palette(palette: Dict[str, str] | None) -> Palette:
    colors = _DEFAULT_PALETTE.copy()
    if palette:
        for key, val in palette.items():
            colors[key] = _hex_to_rgb(val) if isinstance(val, str) else val
    return colors


def render_schedule_image(
    records: List[DayRecord],
    start: date,
    weeks: int,
    out_path: Path,
    palette: Dict[str, str] | None = None,
) -> Path:
    """
    Render a PNG snapshot of the schedule over a given range.

    Args:
        records: Consecutive day records as produced by `resolve_range`
        start: Starting calendar date for the range
        weeks: Number of weeks represented in `records`
        out_path: File path to write the PNG image
        palette: Optional mapping of guardian -> hex color (e.g. {"mom": "#F28B82"})

    Returns:
        Path to the written PNG file.
    """
    if not records:
        raise ValueError("No schedule records to render.")

    if Image is None or ImageDraw is None or ImageFont is None:
        raise RuntimeError(
            "Pillow is required for image exports. Install with `pip install family-schedulekit[visual]`."
        )

    colors = _normalize_palette(palette)

    cell_w = 140
    cell_h = 80
    left_margin = 140
    top_margin = 80
    grid_padding = 20

    width = left_margin + weeks * cell_w + grid_padding
    height = top_margin + len(_WEEKDAYS) * cell_h + grid_padding

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    record_index = _build_index(records)

    # Headers
    draw.text((10, top_margin + cell_h * 0.3), "Day", fill="black", font=font)
    for idx in range(weeks):
        week_records = _records_for_week(records, idx)
        label = _week_label(week_records, start, idx)
        text_x = left_margin + idx * cell_w + cell_w / 2
        draw.text((text_x - 20, 30), label, fill="black", font=font)

    # Day labels and cells
    for row, weekday in enumerate(_WEEKDAYS):
        y0 = top_margin + row * cell_h
        draw.text((10, y0 + cell_h / 2 - 8), weekday.capitalize(), fill="black", font=font)
        for col in range(weeks):
            x0 = left_margin + col * cell_w
            rect = (x0, y0, x0 + cell_w, y0 + cell_h)
            record = record_index.get((col, weekday))
            guardian = (record or {}).get("guardian", "unknown")
            color = colors.get(guardian, colors["unknown"])
            draw.rectangle(rect, fill=color, outline="black", width=1)

            if not record:
                continue

            date_label = record["date"]
            text_y = y0 + 10
            draw.text((x0 + 10, text_y), date_label, fill="black", font=font)

            guardian_name = guardian.capitalize() if guardian else "Unknown"
            draw.text((x0 + 10, text_y + 20), f"{guardian_name}", fill="black", font=font)

            handoff = record.get("handoff")
            if handoff and handoff != "school":
                draw.text((x0 + 10, text_y + 40), _format_handoff(handoff), fill="black", font=font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path, format="PNG")
    return out_path


def _records_for_week(records: List[DayRecord], idx: int) -> List[DayRecord]:
    base = idx * 7
    return records[base : base + 7]


def _build_index(records: List[DayRecord]) -> Dict[Tuple[int, str], DayRecord]:
    index: Dict[Tuple[int, str], DayRecord] = {}
    for idx, record in enumerate(records):
        week_idx = idx // 7
        weekday = str(record.get("weekday", "")).lower()
        if weekday in _WEEKDAYS:
            index[(week_idx, weekday)] = record
    return index


def _week_label(records: List[DayRecord], start: date, week_idx: int) -> str:
    if records:
        cw = records[0]["calendar_week"]
        return f"CW{cw}"
    anchor = start + timedelta(days=week_idx * 7)
    return f"Week {week_idx + 1} ({anchor.isoformat()})"


def _format_handoff(handoff: object) -> str:
    mapping = {
        "after_school": "Handoff: after school",
        "dad_to_mom_by_1pm": "Handoff: Dad→Mom 1 PM",
    }
    return mapping.get(str(handoff), f"Handoff: {handoff}")
