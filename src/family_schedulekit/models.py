from __future__ import annotations
from enum import IntEnum
from typing import Dict, Literal
from pydantic import BaseModel, Field, field_validator

class Weekday(IntEnum):
    MONDAY=0; TUESDAY=1; WEDNESDAY=2; THURSDAY=3; FRIDAY=4; SATURDAY=5; SUNDAY=6
    @classmethod
    def from_python_weekday(cls, i: int) -> "Weekday":
        return Weekday(i)
    def slug(self) -> str:
        return ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"][int(self)]

Guardian = Literal["mom","dad"]

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
    holidays: Dict[str, Guardian] = Field(default_factory=dict)

    @field_validator("holidays")
    @classmethod
    def _validate_holidays(cls, v: Dict[str, Guardian]):
        from datetime import datetime
        for k in v:
            datetime.strptime(k, "%Y-%m-%d")
        return v
