from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

try:  # pragma: no cover - exercised via optional dependency in tests
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - fallback evaluated at runtime
    Image = ImageDraw = ImageFont = None  # type: ignore[assignment]

from .models import Weekday

type DayRecord = dict[str, object]
type Palette = dict[str, tuple[int, int, int]]

_DEFAULT_PALETTE: Palette = {
    "mom": (242, 139, 130),  # soft red
    "dad": (129, 201, 149),  # soft green
    "holiday": (174, 203, 248),  # light blue override
    "unknown": (200, 200, 200),
}

_WEEKDAYS: tuple[Weekday, ...] = tuple(Weekday)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Invalid color value '{value}'. Use 6-character hex (e.g. #F28B82).")
    return tuple(int(value[i : i + 2], 16) for i in range(0, 6, 2))  # type: ignore[return-value]


def _normalize_palette(palette: dict[str, str | tuple[int, int, int]] | None) -> Palette:
    colors = _DEFAULT_PALETTE.copy()
    if palette:
        for key, val in palette.items():
            colors[key] = _hex_to_rgb(val) if isinstance(val, str) else val
    return colors


def render_schedule_image(
    records: list[DayRecord],
    start: date,
    weeks: int,
    out_path: Path,
    palette: dict[str, str | tuple[int, int, int]] | None = None,
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
        raise RuntimeError("Pillow is required for image exports. Install via `uv sync --extra dev` or include Pillow.")

    colors = _normalize_palette(palette)

    # Base layout constants (unscaled)
    base_cell_w = 160
    base_cell_h = 120
    left_margin = 200
    top_margin = 160
    grid_padding = 40
    columns = len(_WEEKDAYS)

    width = left_margin + columns * base_cell_w + grid_padding
    height = top_margin + weeks * base_cell_h + grid_padding

    scale = 2
    scaled_width = width * scale
    scaled_height = height * scale
    cell_w = base_cell_w * scale
    cell_h = base_cell_h * scale
    left_offset = left_margin * scale
    top_offset = top_margin * scale

    image = Image.new("RGB", (scaled_width, scaled_height), "white")
    draw = ImageDraw.Draw(image)

    try:
        header_font = ImageFont.truetype("DejaVuSans.ttf", int(32 * scale))
        cell_font = ImageFont.truetype("DejaVuSans.ttf", int(26 * scale))
    except OSError:
        header_font = ImageFont.load_default()
        cell_font = ImageFont.load_default()

    record_index = _build_index(records)

    def _font_bbox(font: ImageFont.ImageFont, text: str) -> tuple[int, int, int, int]:
        try:
            return font.getbbox(text)
        except AttributeError:
            w, h = font.getsize(text)
            return (0, 0, w, h)

    def _draw_text_center(text: str, x: int, y: int, font: ImageFont.ImageFont):
        bbox = _font_bbox(font, text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((x - tw // 2, y - th // 2), text, fill="black", font=font)

    def _line_height(font: ImageFont.ImageFont) -> int:
        bbox = _font_bbox(font, "Hg")
        return bbox[3] - bbox[1]

    # Column headers (weekdays across the top)
    header_y = top_offset // 2
    for col, weekday in enumerate(_WEEKDAYS):
        center_x = left_offset + col * cell_w + cell_w // 2
        _draw_text_center(weekday.value.capitalize(), center_x, header_y, header_font)

    # Rows for each week
    for row in range(weeks):
        week_records = _records_for_week(records, row)
        week_label = _week_label(week_records, start, row)
        row_center_y = top_offset + row * cell_h + cell_h // 2
        # Week labels on the left
        _draw_text_center(week_label, left_offset // 2, row_center_y, header_font)

        for col, weekday in enumerate(_WEEKDAYS):
            x0 = left_offset + col * cell_w
            y0 = top_offset + row * cell_h
            rect = (x0, y0, x0 + cell_w, y0 + cell_h)
            record = record_index.get((row, weekday))
            guardian = (record or {}).get("guardian", "unknown")
            color = colors.get(guardian, colors["unknown"])
            draw.rectangle(rect, fill=color, outline="black", width=scale)

            if not record:
                continue

            line_x = x0 + 12 * scale
            line_y = y0 + 14 * scale
            line_spacing = _line_height(cell_font) + 6 * scale

            draw.text((line_x, line_y), str(record["date"]), fill="black", font=cell_font)
            draw.text((line_x, line_y + line_spacing), f"{guardian.capitalize()}", fill="black", font=cell_font)

            handoff = record.get("handoff")
            if handoff and handoff != "school":
                draw.text(
                    (line_x, line_y + 2 * line_spacing),
                    _format_handoff(handoff),
                    fill="black",
                    font=cell_font,
                )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    resample = getattr(Image, "Resampling", Image).LANCZOS
    image.resize((width, height), resample=resample).save(out_path, format="PNG")
    return out_path


def _records_for_week(records: list[DayRecord], idx: int) -> list[DayRecord]:
    base = idx * 7
    return records[base : base + 7]


def _build_index(records: list[DayRecord]) -> dict[tuple[int, Weekday], DayRecord]:
    index: dict[tuple[int, Weekday], DayRecord] = {}
    for idx, record in enumerate(records):
        week_idx = idx // 7
        weekday_value = str(record.get("weekday", "")).lower()
        try:
            weekday = Weekday(weekday_value)
        except ValueError:
            continue
        index[(week_idx, weekday)] = record
    return index


def _week_label(records: list[DayRecord], start: date, week_idx: int) -> str:
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
