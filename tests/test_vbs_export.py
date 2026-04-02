"""Tests for _run_vbs_export retry/fallback logic in run.py."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from run import _run_vbs_export

VBS = Path("scripts/calendar_export.vbs")


def _result(returncode: int = 0) -> MagicMock:
    r = MagicMock()
    r.returncode = returncode
    return r


class TestRunVbsExport:
    def test_success_returns_true(self):
        with patch("subprocess.run", return_value=_result(0)):
            assert _run_vbs_export(VBS, 4) is True

    def test_failure_retry_yes_success_returns_true(self):
        with patch("subprocess.run", side_effect=[_result(1), _result(0)]), \
             patch("builtins.input", side_effect=["y"]):
            assert _run_vbs_export(VBS, 4) is True

    def test_failure_retry_no_continue_yes_returns_false(self):
        with patch("subprocess.run", return_value=_result(1)), \
             patch("builtins.input", side_effect=["n", "y"]):
            assert _run_vbs_export(VBS, 4) is False

    def test_failure_retry_yes_second_failure_continue_yes_returns_false(self):
        with patch("subprocess.run", return_value=_result(1)), \
             patch("builtins.input", side_effect=["y", "y"]):
            assert _run_vbs_export(VBS, 4) is False

    def test_failure_retry_no_continue_no_exits(self):
        with patch("subprocess.run", return_value=_result(1)), \
             patch("builtins.input", side_effect=["n", "n"]), \
             pytest.raises(SystemExit):
            _run_vbs_export(VBS, 4)

    def test_failure_retry_yes_second_failure_continue_no_exits(self):
        with patch("subprocess.run", return_value=_result(1)), \
             patch("builtins.input", side_effect=["y", "n"]), \
             pytest.raises(SystemExit):
            _run_vbs_export(VBS, 4)

    def test_timeout_treated_as_failure_continue_yes(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cscript", 120)), \
             patch("builtins.input", side_effect=["n", "y"]):
            assert _run_vbs_export(VBS, 4) is False

    def test_timeout_treated_as_failure_continue_no_exits(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cscript", 120)), \
             patch("builtins.input", side_effect=["n", "n"]), \
             pytest.raises(SystemExit):
            _run_vbs_export(VBS, 4)

    def test_prints_failure_message(self, capsys):
        with patch("subprocess.run", return_value=_result(1)), \
             patch("builtins.input", side_effect=["n", "y"]):
            _run_vbs_export(VBS, 4)
        assert "VBS export failed — is Outlook running?" in capsys.readouterr().out
