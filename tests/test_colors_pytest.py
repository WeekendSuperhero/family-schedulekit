from __future__ import annotations

from unittest.mock import patch

import pytest

from family_schedulekit.colors import (
    color_to_rgb,
    display_color_terminal,
    get_all_css3_colors,
    list_all_colors,
)


def test_get_all_css3_colors():
    """Test retrieval of all CSS3 color names."""
    colors = get_all_css3_colors()
    assert len(colors) == 147
    assert colors == sorted(colors)  # Alphabetical order
    assert "aliceblue" in colors
    assert "red" in colors
    assert colors[0] == "aliceblue"
    assert colors[-1] == "yellowgreen"


@pytest.mark.parametrize(
    "name,expected_rgb",
    [
        ("red", (255, 0, 0)),
        ("blue", (0, 0, 255)),
        ("hotpink", (255, 105, 180)),
        ("steelblue", (70, 130, 180)),
        ("aliceblue", (240, 248, 255)),
        ("black", (0, 0, 0)),
        ("white", (255, 255, 255)),
    ],
)
def test_color_to_rgb_valid(name: str, expected_rgb: tuple[int, int, int]):
    """Test color name to RGB conversion for valid CSS3 names."""
    rgb = color_to_rgb(name)
    assert rgb == expected_rgb


@pytest.mark.parametrize(
    "invalid_name",
    [
        "foocolor",
        "xyz",
        "",
        "invalidcolor",
    ],
)
def test_color_to_rgb_invalid(invalid_name: str):
    """Test that invalid color names raise ValueError."""
    with pytest.raises(ValueError):
        color_to_rgb(invalid_name)


def test_display_color_terminal_dark_background():
    """Test display for dark color (low luminance -> white text)."""
    # Black: lum ~0 <0.5 -> \033[97m (bright white)
    result = display_color_terminal("black", (0, 0, 0), show_value=True)
    assert "\033[48;2;0;0;0m" in result  # BG
    assert "\033[97m" in result  # White text
    assert "black" in result
    assert "RGB(  0,   0,   0)" in result


def test_display_color_terminal_light_background():
    """Test display for light color (high luminance -> black text)."""
    # White: lum=1 >0.5 -> \033[30m (black)
    result = display_color_terminal("white", (255, 255, 255), show_value=True)
    assert "\033[48;2;255;255;255m" in result  # BG
    assert "\033[30m" in result  # Black text
    assert "white" in result
    assert "RGB(255, 255, 255)" in result


def test_display_color_terminal_no_value():
    """Test display without RGB values."""
    result = display_color_terminal("red", (255, 0, 0), show_value=False)
    assert "\033[48;2;255;0;0m" in result
    assert "\033[97m" in result  # Red lum low
    assert "red" in result
    assert "RGB" not in result  # No value shown


def test_display_color_terminal_mid_luminance():
    """Test luminance threshold with mid-gray."""
    # Gray (128,128,128): lum ~0.5, but calc (0.299*128 +0.587*128 +0.114*128)/255 ≈ 128/255=0.5 exactly? Test >0.5 black.
    rgb = (128, 128, 128)
    # lum = (0.299 * 128 + 0.587 * 128 + 0.114 * 128) / 255  # ≈0.50196 >0.5 -> black \033[30m
    result = display_color_terminal("gray", rgb)
    assert "\033[30m" in result  # Black text for lum>0.5


@pytest.mark.parametrize(
    "rgb,lum_threshold,text_code",
    [
        ((0, 0, 0), 0.0, "\033[97m"),  # Dark -> white
        ((255, 255, 255), 1.0, "\033[30m"),  # Light -> black
        ((100, 100, 100), 0.392, "\033[97m"),  # Below 0.5
        ((150, 150, 150), 0.588, "\033[30m"),  # Above 0.5
    ],
)
def test_display_color_terminal_luminance(rgb: tuple[int, int, int], lum_threshold: float, text_code: str):
    """Parametrized luminance text color selection."""
    result = display_color_terminal("test", rgb)
    assert text_code in result


def test_list_all_colors(capsys: pytest.CaptureFixture):
    """Test full list_all_colors output capture."""
    with (
        patch("family_schedulekit.colors.get_all_css3_colors", return_value=["red", "blue"]),
        patch("family_schedulekit.colors.color_to_rgb", side_effect=[(255, 0, 0), (0, 0, 255)]),
    ):
        list_all_colors()

    captured = capsys.readouterr()
    # "147" not printed due to patch (len=2)
    # Better: general structure
    assert "🎨 CSS3 Colors Available" in captured.out
    assert "=" * 80 in captured.out
    assert "Color Preview" in captured.out
    assert "Schema Value" in captured.out
    assert "RGB Values" in captured.out
    # "Total: 2" printed due to patch
    assert "Usage in schedule.json:" in captured.out
    assert '"guardian_1": "coral",' in captured.out
    assert 'You can also use hex values like "#FF1493"' in captured.out


def test_list_all_colors_handles_invalid_safely(capsys: pytest.CaptureFixture):
    """Test safety net for invalid colors in loop (shouldn't happen but covers except)."""
    with (
        patch("family_schedulekit.colors.get_all_css3_colors", return_value=["red", "invalid"]),
        patch(
            "family_schedulekit.colors.color_to_rgb",
            side_effect=[(255, 0, 0), ValueError("Invalid")],
        ),
    ):
        list_all_colors()
    captured = capsys.readouterr()
    assert "(invalid)" in captured.out  # Covers the except block
