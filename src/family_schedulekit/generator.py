from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import yaml

from .models import ScheduleConfigModel
from .resources import load_template


@dataclass(slots=True)
class InitParams:
    guardian_1: str
    guardian_2: str
    children: list[str]
    template: str = "generic"
    outfile: Path = Path("schema/my-schedule.yaml")  # Changed default to YAML
    overwrite: bool = False


def generate_config(params: InitParams) -> str:
    """Generate config content in the format specified by outfile extension."""
    base = load_template(params.template).model_dump(mode="json")
    base["parties"] = {"guardian_1": params.guardian_1, "guardian_2": params.guardian_2, "children": params.children}
    cfg = ScheduleConfigModel.model_validate(base)
    data = cfg.model_dump(mode="json")

    # Determine output format based on file extension
    if params.outfile.suffix in (".yaml", ".yml"):
        # Use block style for better readability
        return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True, width=120, indent=2)
    else:
        return json.dumps(data, indent=2)


def write_config(params: InitParams) -> Path:
    if params.outfile.exists() and not params.overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {params.outfile}")
    params.outfile.parent.mkdir(parents=True, exist_ok=True)
    params.outfile.write_text(generate_config(params), encoding="utf-8")
    return params.outfile
