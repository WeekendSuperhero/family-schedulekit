from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import webcolors

try:  # pragma: no cover - exercised via optional dependency in tests
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - fallback evaluated at runtime
    Image = ImageDraw = ImageFont = None  # type: ignore[assignment]

from .models import Weekday

if TYPE_CHECKING:
    from PIL import ImageDraw as ImageDrawModule
    from PIL import ImageFont as ImageFontModule

    from .models import ScheduleConfigModel

type DayRecord = dict[str, object]
type Palette = dict[str, tuple[int, int, int]]

_DEFAULT_PALETTE: Palette = {
    "guardian_1": (255, 105, 180),  # hotpink
    "guardian_2": (25, 25, 112),  # midnightblue
    "holiday": (173, 216, 230),  # lightblue
    "unknown": (128, 128, 128),  # gray
}

_WEEKDAYS: tuple[Weekday, ...] = tuple(Weekday)
_WEEKDAYS_SUNDAY_FIRST: tuple[Weekday, ...] = (Weekday.SUNDAY,) + _WEEKDAYS[:-1]


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Invalid color value '{value}'. Use 6-character hex (e.g. #F28B82).")
    return tuple(int(value[i : i + 2], 16) for i in range(0, 6, 2))  # type: ignore[return-value]


def _resolve_color_value(value: str | tuple[int, int, int]) -> tuple[int, int, int]:
    """Resolve a color value from CSS3 named color, hex string, or RGB tuple.

    Supports all 147 CSS3 color names via the webcolors library.
    """
    if isinstance(value, tuple):
        return value

    # Check if it's a CSS3 named color
    try:
        rgb = webcolors.name_to_rgb(value.lower())
        return (rgb.red, rgb.green, rgb.blue)
    except ValueError:
        # Not a named color, treat as hex string
        return _hex_to_rgb(value)


def _normalize_palette(palette: dict[str, str | tuple[int, int, int] | int] | None) -> Palette:
    colors = _DEFAULT_PALETTE.copy()
    if palette:
        for key, val in palette.items():
            # Skip non-color fields like swap_shade_percent
            if isinstance(val, int):
                colors[key] = val  # type: ignore
            else:
                colors[key] = _resolve_color_value(val)
    return colors


def _get_text_color(bg_color: tuple[int, int, int]) -> str:
    """
    Determine text color (black or white) based on background luminance.
    Uses relative luminance formula from WCAG 2.0.
    """
    r, g, b = bg_color
    # Calculate relative luminance
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    # Use white text on dark backgrounds, black on light backgrounds
    return "white" if luminance < 0.5 else "black"


def _adjust_color_brightness(color: tuple[int, int, int], percent: int, lighten: bool = True) -> tuple[int, int, int]:
    """
    Adjust color brightness by a percentage.

    Args:
        color: RGB tuple (r, g, b)
        percent: Percentage to adjust (0-100)
        lighten: True to lighten, False to darken

    Returns:
        Adjusted RGB tuple
    """
    r, g, b = color
    factor = percent / 100.0

    if lighten:
        # Lighten: move towards white (255)
        r = int(r + (255 - r) * factor)
        g = int(g + (255 - g) * factor)
        b = int(b + (255 - b) * factor)
    else:
        # Darken: move towards black (0)
        r = int(r * (1 - factor))
        g = int(g * (1 - factor))
        b = int(b * (1 - factor))

    # Clamp to valid RGB range
    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))


def _parse_handoff_time(handoff: str) -> float | None:
    """
    Extract the hour from a handoff description.

    Args:
        handoff: Handoff string (e.g., "guardian_2_to_guardian_1_by_1pm" or "guardian_2_to_guardian_1_by_13:00")

    Returns:
        Hour as float (0-24) or None if no time found
    """
    import re

    # Try to find time patterns like "1pm", "1:00pm", "13:00", "by_1pm", etc.
    # Pattern 1: "by_13:00" or similar 24-hour format
    match = re.search(r"by[_\s]?(\d{1,2}):(\d{2})", handoff, re.IGNORECASE)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        return hour + minute / 60.0

    # Pattern 2: "by_1pm" or "by 1pm" - 12-hour format
    match = re.search(r"by[_\s]?(\d{1,2})\s?(am|pm)", handoff, re.IGNORECASE)
    if match:
        hour = int(match.group(1))
        am_pm = match.group(2).lower()
        if am_pm == "pm" and hour != 12:
            hour += 12
        elif am_pm == "am" and hour == 12:
            hour = 0
        return float(hour)

    # Pattern 3: Just "1pm" without "by"
    match = re.search(r"(\d{1,2})\s?(am|pm)", handoff, re.IGNORECASE)
    if match:
        hour = int(match.group(1))
        am_pm = match.group(2).lower()
        if am_pm == "pm" and hour != 12:
            hour += 12
        elif am_pm == "am" and hour == 12:
            hour = 0
        return float(hour)

    # Pattern 4: 24-hour format like "13:00"
    match = re.search(r"(\d{1,2}):(\d{2})", handoff)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        return hour + minute / 60.0

    return None


def _extract_guardians_from_handoff(handoff: str) -> tuple[str, str] | None:
    """
    Extract from_guardian and to_guardian from handoff description.

    Args:
        handoff: Handoff string like "guardian_2_to_guardian_1_by_1pm"

    Returns:
        Tuple of (from_guardian, to_guardian) or None if not found
    """
    import re

    # Pattern: "guardian_X_to_guardian_Y"
    match = re.search(r"(guardian_[12])_to_(guardian_[12])", handoff)
    if match:
        return (match.group(1), match.group(2))

    return None


def _get_handoff_info_from_config(
    record: DayRecord,
    config: ScheduleConfigModel | None,
) -> tuple[str, str, float] | None:
    """
    Get handoff information from config using the structured HandoffTime.
    Only returns handoff info if the special handoff description is present in the record
    (which the resolver only adds when the handoff conditions are actually met).

    Args:
        record: Day record from resolve_range
        config: Schedule configuration

    Returns:
        Tuple of (from_guardian, to_guardian, hour_as_float) or None if no special handoff applies
    """
    if not config or not record:
        return None

    handoff_str = str(record.get("handoff", ""))
    if not handoff_str or handoff_str == "school":
        return None

    # Try to get weekday from record
    weekday_str = str(record.get("weekday", ""))
    if not weekday_str:
        return None

    try:
        weekday = Weekday(weekday_str.lower())
    except ValueError:
        return None

    # Check if there's a special handoff configured for this weekday
    if weekday in config.handoff.special_handoffs:
        special = config.handoff.special_handoffs[weekday]

        # Check if this specific handoff description is in the record
        # The resolver only adds the special handoff description when the conditions are met
        # (i.e., when there's an actual custody transition matching the special handoff rules)
        if special.description and special.description in handoff_str:
            # This special handoff applies to this day - show gradient
            hour = special.time.hour + special.time.minute / 60.0
            return (special.from_guardian, special.to_guardian, hour)

    return None


def _draw_gradient_cell(
    draw: ImageDrawModule.ImageDraw,
    rect: tuple[int, int, int, int],
    color1: tuple[int, int, int],
    color2: tuple[int, int, int],
    transition_hour: float,
) -> None:
    """
    Draw a vertical gradient from color1 to color2 completing BY the specified hour.

    Args:
        draw: ImageDraw object
        rect: (x0, y0, x1, y1) rectangle bounds
        color1: RGB tuple for the starting color (morning guardian)
        color2: RGB tuple for the ending color (after handoff guardian)
        transition_hour: Hour when handoff completes and color2 is fully visible (0-24, can be fractional)
    """
    x0, y0, x1, y1 = rect
    height = y1 - y0

    # Calculate the pixel position where the transition should be complete
    # Assume day runs from 0:00 (top) to 24:00 (bottom)
    handoff_position = transition_hour / 24.0
    handoff_y = int(y0 + height * handoff_position)

    # Define gradient window - transition happens in the hour(s) before handoff
    # For a smooth gradient, let's use 2 hours before the handoff time
    gradient_hours = 2.0
    gradient_start_hour = max(0, transition_hour - gradient_hours)
    gradient_start_position = gradient_start_hour / 24.0
    gradient_start_y = int(y0 + height * gradient_start_position)

    # Draw the gradient in horizontal strips
    for y in range(y0, y1):
        if y < gradient_start_y:
            # Before gradient starts - solid color1 (first guardian)
            color = color1
        elif y < handoff_y:
            # During gradient - blend from color1 to color2
            progress = (y - gradient_start_y) / max(1, handoff_y - gradient_start_y)
            r = int(color1[0] * (1 - progress) + color2[0] * progress)
            g = int(color1[1] * (1 - progress) + color2[1] * progress)
            b = int(color1[2] * (1 - progress) + color2[2] * progress)
            color = (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
        else:
            # After handoff time - solid color2 (second guardian)
            color = color2

        draw.line([(x0, y), (x1, y)], fill=color)

    # Draw border
    draw.rectangle(rect, outline="black", width=3, fill=None)


def render_schedule_image(
    records: list[DayRecord],
    start: date,
    weeks: int,
    out_path: Path,
    palette: dict[str, str | tuple[int, int, int] | int] | None = None,
    start_weekday: str = "monday",
    guardian_names: dict[str, str] | None = None,
    config: ScheduleConfigModel | None = None,
) -> Path:
    """
    Render a PNG snapshot of the schedule over a given range.

    When config is provided, special handoffs with time information are rendered as gradients
    showing the custody transition visually (e.g., guardian_2 color gradually transitioning to
    guardian_1 color, completing at the handoff time).

    Args:
        records: Consecutive day records as produced by `resolve_range`
        start: Starting calendar date for the range
        weeks: Number of weeks represented in `records`
        out_path: File path to write the PNG image
        palette: Optional mapping of guardian -> hex color (e.g. {"guardian_1": "#F28B82"})
        start_weekday: First day of week in visualization ("monday" or "sunday", default: "monday")
        guardian_names: Optional mapping of guardian_1/guardian_2 to actual names (e.g. {"guardian_1": "Jane", "guardian_2": "John"})
        config: Optional ScheduleConfigModel for accessing handoff time information for gradient rendering.
                When provided, days with special handoffs will show color gradients completing at the handoff time.

    Returns:
        Path to the written PNG file.
    """
    if not records:
        raise ValueError("No schedule records to render.")

    if Image is None or ImageDraw is None or ImageFont is None:
        raise RuntimeError("Pillow is required for image exports. Install via `uv sync --extra dev` or include Pillow.")

    colors = _normalize_palette(palette)

    # Create reverse mapping from actual names to guardian keys for color lookup
    name_to_key: dict[str, str] = {}
    if guardian_names:
        for key, name in guardian_names.items():
            name_to_key[name] = key

    # Helper function to get display name for guardian
    def _get_guardian_display_name(guardian_key: str) -> str:
        """Get the display name for a guardian (actual name if provided, otherwise capitalized key)."""
        if guardian_names and guardian_key in guardian_names:
            return guardian_names[guardian_key]
        return guardian_key.replace("_", " ").title()

    # Helper function to get color key from guardian value (which might be a name or key)
    def _get_color_key(guardian_value: str) -> str:
        """Get the color palette key for a guardian (maps actual names back to guardian_1/guardian_2)."""
        # If it's already a guardian key, return it
        if guardian_value in colors:
            return guardian_value
        # If it's a name, look up the key
        if guardian_value in name_to_key:
            return name_to_key[guardian_value]
        return guardian_value

    # Determine weekday order based on start_weekday
    weekdays = _WEEKDAYS_SUNDAY_FIRST if start_weekday.lower() == "sunday" else _WEEKDAYS

    # Base layout constants (reasonable image size)
    base_cell_w = 250
    base_cell_h = 200
    left_margin = 200
    top_margin = 200
    grid_padding = 50
    bottom_legend_space = 250
    columns = len(weekdays)

    width = left_margin + columns * base_cell_w + grid_padding
    height = top_margin + weeks * base_cell_h + grid_padding + bottom_legend_space

    # No scaling - use dimensions directly
    scaled_width = width
    scaled_height = height
    cell_w = base_cell_w
    cell_h = base_cell_h
    left_offset = left_margin
    top_offset = top_margin

    image = Image.new("RGB", (scaled_width, scaled_height), "white")
    draw = ImageDraw.Draw(image)

    # Try to load bold fonts, fall back to regular if not available
    font_options = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "DejaVuSans-Bold.ttf",
        "Arial-Bold.ttf",
        "Helvetica-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "DejaVuSans.ttf",
    ]

    loaded_font = None
    for font_path in font_options:
        try:
            loaded_font = font_path
            # Test load with small size
            ImageFont.truetype(font_path, 12)
            break
        except OSError:
            continue

    if loaded_font:
        try:
            # Bold fonts for readability
            header_font: ImageFontModule.ImageFont | ImageFontModule.FreeTypeFont = ImageFont.truetype(loaded_font, 30)
            cell_font: ImageFontModule.ImageFont | ImageFontModule.FreeTypeFont = ImageFont.truetype(loaded_font, 20)
            legend_font: ImageFontModule.ImageFont | ImageFontModule.FreeTypeFont = ImageFont.truetype(loaded_font, 24)
        except OSError:
            header_font = ImageFont.load_default()
            cell_font = ImageFont.load_default()
            legend_font = ImageFont.load_default()
    else:
        header_font = ImageFont.load_default()
        cell_font = ImageFont.load_default()
        legend_font = ImageFont.load_default()

    record_index = _build_index(records, start, start_weekday.lower() == "sunday")

    def _font_bbox(font: ImageFontModule.ImageFont | ImageFontModule.FreeTypeFont, text: str) -> tuple[int, int, int, int]:
        try:
            bbox = font.getbbox(text)
            return (int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3]))
        except AttributeError:
            # Fallback for older Pillow versions
            return (0, 0, 10, 10)

    def _draw_text_center(text: str, x: int, y: int, font: ImageFontModule.ImageFont | ImageFontModule.FreeTypeFont):
        bbox = _font_bbox(font, text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((x - tw // 2, y - th // 2), text, fill="black", font=font)

    def _line_height(font: ImageFontModule.ImageFont | ImageFontModule.FreeTypeFont) -> int:
        bbox = _font_bbox(font, "Hg")
        return bbox[3] - bbox[1]

    # Column headers (weekdays across the top)
    header_y = top_offset // 2
    for col, weekday in enumerate(weekdays):
        center_x = left_offset + col * cell_w + cell_w // 2
        _draw_text_center(weekday.value.capitalize(), center_x, header_y, header_font)

    # Rows for each week
    for row in range(weeks):
        week_records = _records_for_week(records, row)
        week_label = _week_label(week_records, start, row)
        row_center_y = top_offset + row * cell_h + cell_h // 2
        # Week labels on the left
        _draw_text_center(week_label, left_offset // 2, row_center_y, header_font)

        for col, weekday in enumerate(weekdays):
            x0 = left_offset + col * cell_w
            y0 = top_offset + row * cell_h
            rect = (x0, y0, x0 + cell_w, y0 + cell_h)
            record = record_index.get((row, weekday))
            guardian = str((record or {}).get("guardian", "unknown"))

            # Determine color - check for swap with custom color first
            is_swap = (record or {}).get("is_swap", False)
            swap_has_custom_color = False
            color: tuple[int, int, int]

            if is_swap and "swap_color" in (record or {}):
                # Swap with custom color specified
                swap_color_value = record["swap_color"]  # type: ignore
                color = swap_color_value if isinstance(swap_color_value, tuple) else colors["unknown"]
                swap_has_custom_color = True
            else:
                # Regular guardian color - map guardian value to color key
                color_key = _get_color_key(guardian)
                base_color = colors.get(color_key, colors["unknown"])

                if is_swap and not swap_has_custom_color:
                    # Swap without custom color - apply automatic shading
                    swap_shade_percent = colors.get("swap_shade_percent", 20)
                    # Decide whether to lighten or darken based on base color luminance
                    r, g, b = base_color
                    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                    # Lighten dark colors, darken light colors
                    lighten = luminance < 0.5
                    color = _adjust_color_brightness(base_color, swap_shade_percent, lighten)  # type: ignore
                else:
                    color = base_color

            # Check if this day has a handoff with time information
            # Priority 1: Use structured handoff info from config
            handoff_info = _get_handoff_info_from_config(record, config) if record else None

            # Priority 2: Fall back to parsing handoff string (for backward compatibility)
            if handoff_info is None and record:
                handoff_str = str(record.get("handoff", ""))
                if handoff_str and handoff_str != "school":
                    handoff_time = _parse_handoff_time(handoff_str)
                    handoff_guardians = _extract_guardians_from_handoff(handoff_str)
                    if handoff_time is not None and handoff_guardians is not None:
                        handoff_info = (handoff_guardians[0], handoff_guardians[1], handoff_time)

            if handoff_info is not None:
                # Draw gradient from one guardian's color to another
                from_guardian, to_guardian, handoff_hour = handoff_info
                from_color = colors.get(from_guardian, colors["unknown"])
                to_color = colors.get(to_guardian, colors["unknown"])
                _draw_gradient_cell(draw, rect, from_color, to_color, handoff_hour)
            else:
                # Draw solid color rectangle
                draw.rectangle(rect, fill=color, outline="black", width=3)

            if not record:
                continue

            # Determine text color based on background color for accessibility
            # For gradient cells, use the average color to determine text color
            if handoff_info is not None:
                from_guardian, to_guardian, _ = handoff_info
                from_color = colors.get(from_guardian, colors["unknown"])
                to_color = colors.get(to_guardian, colors["unknown"])
                avg_color = (
                    (from_color[0] + to_color[0]) // 2,
                    (from_color[1] + to_color[1]) // 2,
                    (from_color[2] + to_color[2]) // 2,
                )
                text_color = _get_text_color(avg_color)
            else:
                text_color = _get_text_color(color)

            # Center text in cell
            cell_center_x = x0 + cell_w // 2
            cell_center_y = y0 + cell_h // 2

            # Prepare all text lines
            lines = [str(record["date"]), _get_guardian_display_name(guardian)]
            handoff = record.get("handoff")
            if handoff and handoff != "school":
                lines.append(_format_handoff(handoff))

            # Add swap note if present
            swap_note = record.get("swap_note")
            if swap_note:
                lines.append(f"({swap_note})")

            # Calculate total height of text block
            line_spacing = _line_height(cell_font) + 5
            total_text_height = len(lines) * line_spacing

            # Start drawing from centered position
            start_y = cell_center_y - total_text_height // 2

            for i, line in enumerate(lines):
                bbox = _font_bbox(cell_font, line)
                text_width = bbox[2] - bbox[0]
                text_x = cell_center_x - text_width // 2
                text_y = start_y + i * line_spacing
                draw.text((text_x, text_y), line, fill=text_color, font=cell_font)

    # Draw legend at the bottom
    legend_y = top_offset + weeks * cell_h + grid_padding
    legend_x_start = left_offset
    legend_box_size = 100
    legend_spacing = 150

    # Get unique guardians from records
    guardians = set()
    for record in records:
        guardian = str((record or {}).get("guardian", ""))
        if guardian and guardian != "unknown":
            guardians.add(guardian)

    # Draw legend items
    x_pos = legend_x_start
    for idx, guardian in enumerate(sorted(guardians)):
        color_key = _get_color_key(guardian)
        color = colors.get(color_key, colors["unknown"])
        text_color = _get_text_color(color)

        # Draw color box
        box_rect = (x_pos, legend_y, x_pos + legend_box_size, legend_y + legend_box_size)
        draw.rectangle(box_rect, fill=color, outline="black", width=4)

        # Draw label
        label_x = x_pos + legend_box_size + 30
        label_y = legend_y + legend_box_size // 2
        guardian_display = _get_guardian_display_name(guardian)
        draw.text((label_x, label_y - _line_height(legend_font) // 2), guardian_display, fill="black", font=legend_font)

        # Calculate width for next item
        bbox = _font_bbox(legend_font, guardian_display)
        text_width = bbox[2] - bbox[0]
        x_pos += legend_box_size + text_width + legend_spacing

    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path, format="PNG")
    return out_path


def _records_for_week(records: list[DayRecord], idx: int) -> list[DayRecord]:
    base = idx * 7
    return records[base : base + 7]


def _build_index(records: list[DayRecord], start: date, sunday_first: bool = False) -> dict[tuple[int, Weekday], DayRecord]:
    index: dict[tuple[int, Weekday], DayRecord] = {}

    for idx, record in enumerate(records):
        date_str = str(record.get("date", ""))
        try:
            record_date = date.fromisoformat(date_str)
        except (ValueError, TypeError):
            continue

        weekday_value = str(record.get("weekday", "")).lower()
        try:
            weekday = Weekday(weekday_value)
        except ValueError:
            continue

        if sunday_first:
            # For Sunday-first layout, calculate which visual row this date belongs to
            # Adjust so that Sunday is day 0 of each visual week
            days_since_start = (record_date - start).days
            # Shift by 1 if start date is not Sunday, to align weeks properly
            start_weekday_num = start.weekday()  # 0=Mon, 6=Sun
            if start_weekday_num == 6:  # Start is Sunday
                week_idx = days_since_start // 7
            else:
                # Shift to make the previous/same Sunday the start of week 0
                days_since_sunday = (start_weekday_num + 1) % 7  # Days from last Sunday
                adjusted_days = days_since_start + days_since_sunday
                week_idx = adjusted_days // 7
        else:
            # Monday-first: simple division
            week_idx = idx // 7

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
        "guardian_2_to_guardian_1_by_1pm": "Handoff: Guardian 2→Guardian 1 1 PM",
    }
    return mapping.get(str(handoff), f"Handoff: {handoff}")
