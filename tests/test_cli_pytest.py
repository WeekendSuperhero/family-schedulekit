from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from family_schedulekit import cli


@pytest.fixture
def capsys_disabled():
    """Disable capsys for sys.exit calls."""
    with patch.object(pytest, "capsys", lambda: None):
        yield


def test_help(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["family-schedulekit", "--help"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "usage: family-schedulekit" in captured.out


def test_no_args_error(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["family"])
