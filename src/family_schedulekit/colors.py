"""Color utilities and CLI display for CSS3 named colors."""

from __future__ import annotations

import webcolors


def get_all_css3_colors() -> list[str]:
    """Get all CSS3 color names supported by the library.

    Returns:
        List of 147 CSS3 color names in alphabetical order.
    """
    return webcolors.names("css3")


def color_to_rgb(name: str) -> tuple[int, int, int]:
    """Convert a CSS3 color name to RGB tuple.

    Args:
        name: CSS3 color name (case-insensitive)

    Returns:
        RGB tuple (r, g, b) with values 0-255

    Raises:
        ValueError: If color name is not recognized
    """
    rgb = webcolors.name_to_rgb(name.lower())
    return (rgb.red, rgb.green, rgb.blue)


def display_color_terminal(name: str, rgb: tuple[int, int, int], show_value: bool = True) -> str:
    """Display a color in the terminal with ANSI escape codes.

    Args:
        name: Color name to display
        rgb: RGB tuple (r, g, b)
        show_value: Whether to show the schema value (default: True)

    Returns:
        Formatted string with color preview and name
    """
    r, g, b = rgb

    # ANSI escape codes for 24-bit color (truecolor)
    # Format: \033[48;2;R;G;Bm for background color
    bg_color = f"\033[48;2;{r};{g};{b}m"

    # Calculate luminance to determine text color (black or white)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    text_color = "\033[30m" if luminance > 0.5 else "\033[97m"  # black or white

    # Reset code
    reset = "\033[0m"

    # Create color swatch (8 spaces with background color)
    swatch = f"{bg_color}{text_color}  {name:16s}  {reset}"

    if show_value:
        # Show the exact value to use in schema
        return f"{swatch}  →  {name:20s}  RGB({r:3d}, {g:3d}, {b:3d})"
    else:
        return swatch


def list_all_colors() -> None:
    """Print all CSS3 colors with terminal preview."""
    colors = get_all_css3_colors()

    print("\n🎨 CSS3 Colors Available (147 total)\n")
    print("=" * 80)
    print(f"{'Color Preview':<22} {'Schema Value':<22} {'RGB Values'}")
    print("=" * 80)

    for name in colors:
        try:
            rgb = color_to_rgb(name)
            print(display_color_terminal(name, rgb))
        except ValueError:
            # Shouldn't happen with CSS3 names, but be safe
            print(f"  {name:20s}  (invalid)")

    print("=" * 80)
    print(f"\nTotal: {len(colors)} CSS3 color names")
    print("\nUsage in schedule.json:")
    print('  "visualization": {')
    print('    "guardian_1": "coral",')
    print('    "guardian_2": "steelblue",')
    print('    "holiday": "gold"')
    print("  }")
    print('\nYou can also use hex values like "#FF1493"')
    print()
