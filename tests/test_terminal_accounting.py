"""Purged controller receipts require positive native terminal accounting."""

import json
import subprocess
from types import SimpleNamespace

import pytest

from fungen_operator.execution import Executor
from fungen_operator.fixture import create_fixture
from fungen_operator.harness import Harness


@pytest.fixture
def executor(tmp_path):
    return Executor(create_fixture(tmp_path / "fixture"))


def observations(monkeypatch, bjobs, accounting="", code=0, error=None):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        if command[0] == "bjobs":
            return SimpleNamespace(stdout=json.dumps({"RECORDS": [bjobs]}), stderr="", returncode=0)
        assert command == ["bacct", "-l", "123"]
        assert kwargs["timeout"] == 60
        if error:
            raise error
        return SimpleNamespace(stdout=accounting, stderr="", returncode=code)

    monkeypatch.setattr("fungen_operator.execution.subprocess.run", run)
    return calls


@pytest.mark.parametrize("state", ["DONE", "EXIT"])
def test_purged_job_uses_matching_terminal_accounting(executor, monkeypatch, state):
    calls = observations(monkeypatch, {"ERROR": "Job <123> is not found"},
                         f"Accounting information\nJob <123>, Job Name <test>, User <user>,\n"
                         f"                     Status <{state}>, Queue <premium>, Command <echo RUN>\n")
    result = executor.scheduler("123")
    assert result == {"job_id": "123", "status": state, "exit_code": None, "source": "bacct"}
    assert len(calls) == 2


@pytest.mark.parametrize("body,code", [
    ("No matching job found", 0),
    ("Job <124>, Status <EXIT>, Command <true>\n", 0),
    ("Job <123>, Status <RUN>, Command <true>\n", 0),
    ("Job <123>, Status <EXIT>, Command <true>\n", 1),
    ("Job <123>, Command <echo 'Status <EXIT>'>\n", 0),
])
def test_absent_or_invalid_accounting_stays_unknown(executor, monkeypatch, body, code):
    observations(monkeypatch, {"ERROR": "Job <123> is not found"}, body, code)
    assert executor.scheduler("123")["status"] == "UNKNOWN"


@pytest.mark.parametrize("record", [
    {"JOBID": "123", "STAT": "RUN", "EXIT_CODE": ""},
    {"ERROR": "Scheduler connection failed"},
    {},
])
def test_other_scheduler_responses_never_use_accounting(executor, monkeypatch, record):
    calls = observations(monkeypatch, record)
    assert executor.scheduler("123")["status"] == record.get("STAT", "UNKNOWN")
    assert len(calls) == 1


@pytest.mark.parametrize("error", [OSError("unavailable"), subprocess.TimeoutExpired("bacct", 60)])
def test_accounting_failure_stays_unknown(executor, monkeypatch, error):
    observations(monkeypatch, {"ERROR": "Job <123> is not found"}, error=error)
    assert executor.scheduler("123")["status"] == "UNKNOWN"


def test_idle_reconciles_purged_receipt_through_executor(executor, monkeypatch):
    import nbformat

    observations(monkeypatch, {"ERROR": "Job <123> is not found"},
                 "Job <123>, Status <EXIT>, Command <true>\n")
    cell = nbformat.v4.new_code_cell(metadata={"fungen": {
        "action": "initiate_run", "result": {"job_id": "123", "scheduler": {"status": "PEND"}},
        "slots": {"bindings": {"log_stem": str(executor.deployment.run_root + "/old")}}}})
    nb = nbformat.v4.new_notebook(cells=[cell])
    harness = Harness(executor.deployment, executor)
    harness._idle(nb)
    assert cell.metadata.fungen.result.scheduler.status == "EXIT"
    assert cell.metadata.fungen.result.terminal_observed
