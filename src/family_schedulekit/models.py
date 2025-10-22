from __future__ import annotations
from datetime import datetime
from enum import StrEnum
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class Weekday(StrEnum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"

    @classmethod
    def from_python_weekday(cls, i: int) -> "Weekday":
        return tuple(cls)[i]

    def slug(self) -> str:
        return self.value


type Guardian = Literal["mom", "dad"]


class WeekdayRules(BaseModel):
    monday: Guardian
    tuesday: Guardian
    wednesday: Guardian
    thursday: Guardian


class SundayRule(BaseModel):
    cw_mod4_equals_0: Guardian
    otherwise: Guardian


class WeekendOdd(BaseModel):
    friday: Guardian
    saturday: Guardian
    sunday: Guardian


class WeekendEven(BaseModel):
    friday: Guardian
    saturday: Guardian
    sunday: SundayRule


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


class Handoff(BaseModel):
    weekdays: Literal["school"]
    sunday_dad_to_mom: Literal["by_1pm"]


class ScheduleConfigModel(BaseModel):
    parties: Parties
    calendar_week_system: Literal["ISO8601"]
    handoff: Handoff
    rules: Rules
    holidays: dict[str, Guardian] = Field(default_factory=dict)

    @field_validator("holidays")
    @classmethod
    def _validate_holidays(cls, v: dict[str, Guardian]):
        for k in v:
            datetime.strptime(k, "%Y-%m-%d")
        return v
