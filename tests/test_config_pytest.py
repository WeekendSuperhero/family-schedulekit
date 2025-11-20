import importlib
import os
from pathlib import Path

import pytest

import family_schedulekit.config as config_mod


@pytest.fixture
def isolated_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Patch HOME env, reload module, create config_dir, yield."""
    test_home = tmp_path / "fake_home"
    monkeypatch.setenv("HOME", str(test_home))
    importlib.reload(config_mod)
    config_dir = config_mod.DEFAULT_CONFIG_DIR  # Now uses fake HOME
    config_dir.mkdir(parents=True, exist_ok=True)
    yield config_dir
    importlib.reload(config_mod)  # Reset for next test


def test_config_exists_yaml(isolated_config):
    (isolated_config / "schedule.yaml").touch()
    assert config_mod.config_exists()


def test_config_exists_json(isolated_config):
    (isolated_config / "schedule.json").touch()
    assert config_mod.config_exists()


def test_config_exists_none(isolated_config):
    assert not config_mod.config_exists()


def test_get_config_path_yaml(isolated_config):
    yaml_path = isolated_config / "schedule.yaml"
    yaml_path.touch()
    assert config_mod.get_config_path() == yaml_path


def test_get_config_path_json_fallback(isolated_config):
    json_path = isolated_config / "schedule.json"
    json_path.touch()
    assert config_mod.get_config_path() == json_path


def test_get_config_path_default(isolated_config):
    assert config_mod.get_config_path() == config_mod.DEFAULT_CONFIG_FILE


def test_ensure_config_dir_creates(isolated_config):
    # Temporarily remove dir for test
    if isolated_config.exists():
        isolated_config.rmdir()
    assert not isolated_config.exists()
    result = config_mod.ensure_config_dir()
    assert isolated_config.exists()
    assert result == isolated_config
    assert isolated_config.is_dir()


def test_ensure_config_dir_idempotent(isolated_config):
    result = config_mod.ensure_config_dir()
    assert result == isolated_config
