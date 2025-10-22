from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List
from .models import ScheduleConfigModel
from .resources import load_template


@dataclass
class InitParams:
    mom: str
    dad: str
    children: List[str]
    template: str = "generic"
    outfile: Path = Path("schema/my-schedule.json")
    overwrite: bool = False


def generate_config(params: InitParams) -> str:
    base = load_template(params.template).model_dump(mode="json")
    base["parties"] = {"mom": params.mom, "dad": params.dad, "children": params.children}
    cfg = ScheduleConfigModel.model_validate(base)
    return json.dumps(cfg.model_dump(mode="json"), indent=2)


def write_config(params: InitParams) -> Path:
    if params.outfile.exists() and not params.overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {params.outfile}")
    params.outfile.parent.mkdir(parents=True, exist_ok=True)
    params.outfile.write_text(generate_config(params), encoding="utf-8")
    return params.outfile
