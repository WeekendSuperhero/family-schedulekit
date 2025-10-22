from __future__ import annotations
from importlib import resources
from typing import List
from .models import ScheduleConfigModel

_DATA_DIR = "data"
_TEMPLATE_INDEX = {
    "generic": "example-schedule.generic.json",
}


def list_templates() -> List[str]:
    return list(_TEMPLATE_INDEX.keys())


def default_config_text() -> str:
    return (
        resources.files(__package__)
        .joinpath(_DATA_DIR)
        .joinpath(_TEMPLATE_INDEX["generic"])
        .read_text(encoding="utf-8")
    )


def load_default_config() -> ScheduleConfigModel:
    return ScheduleConfigModel.model_validate_json(default_config_text())


def load_template(name: str) -> ScheduleConfigModel:
    key = name.strip().lower()
    if key not in _TEMPLATE_INDEX:
        raise ValueError(f"Unknown template '{name}'. Available: {', '.join(list_templates())}")
    txt = (
        resources.files(__package__)
        .joinpath(_DATA_DIR)
        .joinpath(_TEMPLATE_INDEX[key])
        .read_text(encoding="utf-8")
    )
    return ScheduleConfigModel.model_validate_json(txt)
