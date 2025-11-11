from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Named color presets for easy configuration
type NamedColor = Literal[
    "pink",
    "hot_pink",
    "deep_pink",
    "blue",
    "dark_blue",
    "midnight_blue",
    "light_blue",
    "sky_blue",
    "green",
    "mint_green",
    "forest_green",
    "purple",
    "lavender",
    "orange",
    "coral",
    "red",
    "crimson",
    "yellow",
    "gold",
    "gray",
    "grey",
    "light_gray",
    "light_grey",
]

type ColorValue = NamedColor | str  # Named color or hex string like "#FF1493"


class Weekday(StrEnum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"

    @classmethod
    def from_python_weekday(cls, i: int) -> Weekday:
        return tuple(cls)[i]

    def slug(self) -> str:
        return self.value


type Guardian = Literal["mom", "dad"]


class WeekdayRules(BaseModel):
    monday: Guardian
    tuesday: Guardian
    wednesday: Guardian
    thursday: Guardian


class CalendarWeekModuloRule(BaseModel):
    """Rule that applies based on calendar week modulo operation.

    Example: For modulo=4, remainder=0, this applies when calendar_week % 4 == 0
    """

    modulo: int = Field(ge=2, description="Divisor for modulo operation")
    remainder: int = Field(ge=0, description="Target remainder value")
    guardian: Guardian = Field(description="Guardian when rule matches")

    @field_validator("remainder")
    @classmethod
    def _validate_remainder(cls, v: int, info) -> int:
        modulo = info.data.get("modulo")
        if modulo is not None and v >= modulo:
            raise ValueError(f"remainder must be less than modulo (got {v} >= {modulo})")
        return v


class WeekdayRule(BaseModel):
    """Flexible rule for any weekday that can use modulo conditions or simple guardian assignment."""

    modulo_rules: list[CalendarWeekModuloRule] = Field(default_factory=list)
    otherwise: Guardian = Field(description="Guardian when no modulo rules match")


class WeekendOdd(BaseModel):
    friday: Guardian
    saturday: Guardian
    sunday: Guardian


class WeekendEven(BaseModel):
    friday: Guardian | WeekdayRule
    saturday: Guardian | WeekdayRule
    sunday: Guardian | WeekdayRule


class Weekends(BaseModel):
    odd_weeks: WeekendOdd
    even_weeks: WeekendEven


class Rules(BaseModel):
    weekdays: WeekdayRules
    weekends: Weekends


class Parties(BaseModel):
    mom: str
    dad: str
    children: list[str]


class HandoffTime(BaseModel):
    """Structured time representation for handoffs.

    Examples:
      - 1:00 PM: HandoffTime(hour=1, minute=0, use_24h=False)
      - 13:00: HandoffTime(hour=13, minute=0, use_24h=True)
      - By 1 PM: HandoffTime(hour=1, minute=0, use_24h=False, by=True)
    """

    hour: int = Field(ge=0, le=23, description="Hour (0-23)")
    minute: int = Field(default=0, ge=0, le=59, description="Minute (0-59)")
    use_24h: bool = Field(default=False, description="Use 24-hour format (default: 12-hour AM/PM)")
    by: bool = Field(default=False, description="Indicates 'by this time' rather than 'at this time'")

    def format(self) -> str:
        """Format the time as a human-readable string."""
        if self.use_24h:
            time_str = f"{self.hour:02d}:{self.minute:02d}"
        else:
            # Convert to 12-hour format
            hour_12 = self.hour % 12
            if hour_12 == 0:
                hour_12 = 12
            am_pm = "AM" if self.hour < 12 else "PM"
            if self.minute == 0:
                time_str = f"{hour_12}{am_pm}"
            else:
                time_str = f"{hour_12}:{self.minute:02d}{am_pm}"

        return f"by {time_str}" if self.by else time_str


class SpecialHandoff(BaseModel):
    """A special handoff rule that applies under specific conditions.

    Example: Dad returns kids to Mom by 1 PM on Sundays when CW % 4 == 0
    """

    from_guardian: Guardian = Field(description="Guardian handing off custody")
    to_guardian: Guardian = Field(description="Guardian receiving custody")
    time: HandoffTime = Field(description="Time of handoff")
    description: str | None = Field(default=None, description="Human-readable description")


class WeekdayHandoffs(BaseModel):
    """Handoff rules for weekdays (Monday-Thursday)."""

    location: str = Field(default="school", description="Where weekday handoffs occur")
    time: str | None = Field(default=None, description="Specific time if needed")


class Handoff(BaseModel):
    """Handoff logistics and timing rules."""

    weekdays: WeekdayHandoffs | Literal["school"] = Field(default="school", description="Weekday handoff rules (simple location or detailed object)")
    special_handoffs: dict[Weekday, SpecialHandoff] = Field(default_factory=dict, description="Special handoff rules for specific weekdays")


class VisualizationPalette(BaseModel):
    """Color palette for PNG calendar visualizations.

    Supports named colors (e.g., 'pink', 'blue') or hex strings (e.g., '#FF1493').
    """

    mom: ColorValue = Field(default="hot_pink", description="Color for mom's custody days")
    dad: ColorValue = Field(default="midnight_blue", description="Color for dad's custody days")
    holiday: ColorValue | None = Field(default="light_blue", description="Color for holiday overrides")
    unknown: ColorValue | None = Field(default="gray", description="Color for unknown/error states")


class ScheduleConfigModel(BaseModel):
    version: str = Field(default="1.0.0", description="Schema version for compatibility tracking")
    parties: Parties
    calendar_week_system: Literal["ISO8601"]
    handoff: Handoff
    rules: Rules
    holidays: dict[str, Guardian] = Field(default_factory=dict)
    visualization: VisualizationPalette = Field(default_factory=VisualizationPalette, description="Color palette for PNG exports")

    @field_validator("holidays")
    @classmethod
    def _validate_holidays(cls, v: dict[str, Guardian]):
        for k in v:
            datetime.strptime(k, "%Y-%m-%d")
        return v
