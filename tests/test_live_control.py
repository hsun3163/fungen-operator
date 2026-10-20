"""Approval and live membership are required before a recorded job control cell."""
import asyncio
import copy
import json
from pathlib import Path

import pytest
from mcp import Client
from mcp.types import ElicitResult
from pydantic import ValidationError

from fungen_operator.actions import InspectRun, render
from fungen_operator.execution import Executor
from fungen_operator.fixture import create_fixture
from fungen_operator.harness import Harness
from fungen_operator.live_control import ControlRun
from fungen_operator.notebook import Notebook, active, verify
from fungen_operator.server import create_server


class RecordingExecution:
    can_schedule = True
    can_inspect = True

    def __init__(self):
        self.executed = []

    def execute(self, cell, *folder):
        self.executed.append(cell.source)
        return {"status": "controlled", "job_ids": list(cell.metadata.fungen.slots.bindings.job_ids),
                "receipt": "native control receipt"}


@pytest.fixture
def control(tmp_path, monkeypatch):
    d = create_fixture(tmp_path / "fixture")
    request = ControlRun(notebook=str(Path(d.run_root, "operator.ipynb")), operation="kill", job_ids=["123"])
    executor = RecordingExecution()
    h = Harness(d, executor)
    snapshot = {"scheduler_ok": True, "count": 1, "dead_children": [{"wrapper_job_id": "123"}],
                "jobs": {"123": {"membership": True, "status": "RUN", "queue": "premium"},
                         "456": {"membership": True, "status": "PEND", "queue": "express", "pending_minutes": 20},
                         "789": {"membership": False, "status": "RUN", "membership_reason": "job is outside this run"}}}
    monkeypatch.setattr(h, "_job_snapshot", lambda *args: copy.deepcopy(snapshot))
    return h, executor, request, snapshot


def proof(proposal):
    return {"fingerprint": proposal["fingerprint"], "channel": "mcp_human_elicitation"}


@pytest.mark.parametrize("operation,queue,literal", [("kill", None, "bkill 123"),
    ("switch_queue", "premium", "bswitch premium 123"), ("switch_queue", "express", "bswitch express 123")])
def test_exact_command_receipt_and_rerender(control, operation, queue, literal):
    h, executor, request, _ = control
    request = request.model_copy(update={"operation": operation, "queue": queue})
    proposal = h.propose_control(request)
    assert proposal["command"] == literal.split()
    assert not Path(request.notebook).exists()
    with pytest.raises(ValueError, match="approval"):
        h.control_run(proposal)
    result = h.control_run(proposal, proof(proposal))
    assert result["status"] == "controlled"
    nb = Notebook(request.notebook).read()
    assert active(nb)[0].source == "%%bash\nset -eo pipefail\n" + literal + "\n"
    assert active(nb)[0].metadata.fungen.result.receipt == "native control receipt"
    verify(nb)
    assert executor.executed == [active(nb)[0].source]
    assert h.replay(request.notebook) == []
    assert len(executor.executed) == 1


@pytest.mark.parametrize("operation,queue", [("kill", None), ("switch_queue", "premium")])
def test_outside_id_refuses_entire_selection(control, operation, queue):
    h, executor, request, _ = control
    request = request.model_copy(update={"operation": operation, "queue": queue, "job_ids": ["123", "789"]})
    result = h.propose_control(request)
    assert result["status"] == "refused"
    assert result["refusals"] == [{"job_id": "789", "reason": "job is outside this run"}]
    assert not executor.executed and not Path(request.notebook).exists()


@pytest.mark.parametrize("selector,expected", [({"kind": "dead_child_wrappers"}, ["123"]),
    ({"kind": "pending", "queue": "express", "min_pending_minutes": 10}, ["456"])])
def test_selectors_freeze_exact_list_before_approval(control, selector, expected):
    h, executor, request, snapshot = control
    request = ControlRun(**{**request.model_dump(), "job_ids": None, "selector": selector})
    proposal = h.propose_control(request)
    assert proposal["job_ids"] == expected
    snapshot["jobs"]["999"] = {"membership": True, "status": "PEND", "queue": "express", "pending_minutes": 100}
    snapshot["dead_children"].append({"wrapper_job_id": "999"})
    h.control_run(proposal, proof(proposal))
    assert executor.executed == ["%%bash\nset -eo pipefail\nbkill " + expected[0] + "\n"]


def test_rechecks_live_membership_after_approval(control):
    h, executor, request, snapshot = control
    proposal = h.propose_control(request)
    snapshot["jobs"]["123"]["membership"] = False
    result = h.control_run(proposal, proof(proposal))
    assert result["status"] == "refused"
    assert not executor.executed and not Path(request.notebook).exists()


def test_no_record_and_unavailable_scheduler_fail_closed(control):
    h, executor, request, snapshot = control
    snapshot["scheduler_ok"] = False
    assert h.propose_control(request)["status"] == "refused"
    snapshot["scheduler_ok"] = True
    snapshot["jobs"].pop("123")
    assert h.propose_control(request)["status"] == "refused"
    assert not executor.executed


def test_changed_ids_invalidate_approval(control):
    h, executor, request, _ = control
    proposal = h.propose_control(request)
    approval = proof(proposal)
    proposal["bindings"]["job_ids"] = ["456"]
    with pytest.raises(ValueError, match="stale"):
        h.control_run(proposal, approval)
    assert not executor.executed


def test_staged_control_rechecks_exact_ids_at_host_execution(control):
    h, executor, request, snapshot = control
    executor.can_schedule = False
    proposal = h.propose_control(request)
    result = h.control_run(proposal, proof(proposal))
    assert result["status"] == "host_approval_required"
    assert not executor.executed
    snapshot["jobs"]["123"]["membership"] = False
    executor.can_schedule = True
    with pytest.raises(ValueError, match="refused"):
        h.execute_pending(request.notebook, result["cell_id"])
    assert not executor.executed


@pytest.mark.parametrize("answer", ["decline", "cancel", "false", "unsupported"])
def test_mcp_decline_cancel_and_unsupported_leave_jobs_and_notebook(control, answer):
    h, executor, request, _ = control
    asked = []
    async def respond(ctx, params):
        asked.append(params.message)
        if answer == "false":
            return ElicitResult(action="accept", content={"approve": False})
        return ElicitResult(action=answer)
    async def exercise():
        kwargs = {} if answer == "unsupported" else {"elicitation_callback": respond}
        async with Client(create_server(h), **kwargs) as client:
            if answer == "unsupported":
                with pytest.raises(Exception, match="elicitation capability"):
                    await client.call_tool("control_run", {"request": request.model_dump()})
                return
            result = await client.call_tool("control_run", {"request": request.model_dump()})
            if answer != "unsupported":
                assert not result.is_error
                assert result.structured_content["status"] == "approval_declined"
    asyncio.run(exercise())
    assert not executor.executed and not Path(request.notebook).exists()
    if asked:
        assert "bkill 123" in asked[0] and '"job_ids": ["123"]' in asked[0]


def test_mcp_accept_stages_visible_command(control):
    h, executor, request, _ = control
    executor.can_schedule = False
    async def accept(ctx, params):
        assert "bkill 123" in params.message
        return ElicitResult(action="accept", content={"approve": True})
    async def exercise():
        async with Client(create_server(h), elicitation_callback=accept) as client:
            result = await client.call_tool("control_run", {"request": request.model_dump()})
            assert not result.is_error, result
            assert result.structured_content["status"] == "host_approval_required"
    asyncio.run(exercise())
    assert not executor.executed
    cell = active(Notebook(request.notebook).read())[0]
    assert cell.source.endswith("bkill 123\n")
    assert cell.metadata.fungen.approval.channel == "mcp_human_elicitation"


@pytest.mark.parametrize("update", [{"job_ids": ["123;id"]}, {"job_ids": ["0"]}, {"job_ids": []},
    {"job_ids": [123]}, {"job_ids": ["123", "123"]}, {"operation": "bkill"},
    {"operation": "switch_queue"}, {"queue": "premium"}, {"job_ids": None},
    {"selector": {"kind": "dead_child_wrappers"}}, {"job_ids": None, "selector": {"kind": "pending"}},
    {"dead_child_grace_minutes": True}, {"approve": True}])
def test_control_types_refuse_injection_and_ambiguous_selection(control, update):
    _, _, request, _ = control
    with pytest.raises(ValidationError):
        ControlRun(**{**request.model_dump(), **update})


def test_native_executor_retains_control_output(control, monkeypatch):
    h, _, request, _ = control
    binary = Path(h.deployment.conda_env, "bin/bkill")
    binary.write_text('#!/bin/sh\nprintf "Job <%s> is being terminated\\n" "$1"\n')
    binary.chmod(0o755)
    h.executor = Executor(h.deployment)
    # The executor constructs its own harness to revalidate directly at execution.
    monkeypatch.setattr(Harness, "_job_snapshot", lambda *a: {"scheduler_ok": True, "jobs": {
        "123": {"membership": True, "status": "RUN"}}})
    proposal = h.propose_control(request)
    result = h.control_run(proposal, proof(proposal))
    assert result["status"] == "controlled"
    assert result["command"] == ["bkill", "123"]
    assert "Job <123> is being terminated" in result["receipt"]
    verify(Notebook(request.notebook).read())


def test_concurrent_identical_selectors_approve_their_own_exact_ids(control):
    h, executor, request, snapshot = control
    request = ControlRun(**{**request.model_dump(), "job_ids": None,
        "selector": {"kind": "pending", "queue": "express", "min_pending_minutes": 10}})
    messages = []

    async def exercise():
        first_asked = asyncio.Event()
        second_asked = asyncio.Event()
        first_completed = asyncio.Event()

        async def respond(ctx, params):
            messages.append(params.message)
            if len(messages) == 1:
                first_asked.set()
                await second_asked.wait()
                return ElicitResult(action="accept", content={"approve": True})
            second_asked.set()
            await first_completed.wait()
            return ElicitResult(action="decline")

        async with Client(create_server(h), mode="legacy", elicitation_callback=respond) as client:
            first = asyncio.create_task(client.call_tool("control_run", {"request": request.model_dump()}))
            await asyncio.wait_for(first_asked.wait(), timeout=10)
            snapshot["jobs"]["999"] = {"membership": True, "status": "PEND",
                "queue": "express", "pending_minutes": 100}
            second = asyncio.create_task(client.call_tool("control_run", {"request": request.model_dump()}))
            try:
                first_result = await asyncio.wait_for(first, timeout=10)
            finally:
                first_completed.set()
            second_result = await asyncio.wait_for(second, timeout=10)
            assert not first_result.is_error and not second_result.is_error
            assert first_result.structured_content["job_ids"] == ["456"]
            assert second_result.structured_content["status"] == "approval_declined"
            assert second_result.structured_content["job_ids"] == ["456", "999"]

    asyncio.run(exercise())
    assert '"job_ids": ["456"]' in messages[0]
    assert '"job_ids": ["456", "999"]' in messages[1]
    assert executor.executed == ["%%bash\nset -eo pipefail\nbkill 456\n"]


def test_modern_selector_change_requires_new_exact_id_approval(control):
    h, executor, request, snapshot = control
    request = ControlRun(**{**request.model_dump(), "job_ids": None,
        "selector": {"kind": "pending", "queue": "express", "min_pending_minutes": 10}})
    messages = []

    async def respond(ctx, params):
        messages.append(params.message)
        if len(messages) == 1:
            snapshot["jobs"]["999"] = {"membership": True, "status": "PEND",
                "queue": "express", "pending_minutes": 100}
            return ElicitResult(action="accept", content={"approve": True})
        return ElicitResult(action="decline")

    async def exercise():
        async with Client(create_server(h), mode="2026-07-28", elicitation_callback=respond) as client:
            result = await client.call_tool("control_run", {"request": request.model_dump()})
            assert not result.is_error
            assert result.structured_content["status"] == "approval_declined"
            assert result.structured_content["job_ids"] == ["456", "999"]

    asyncio.run(exercise())
    assert len(messages) == 2
    assert '"job_ids": ["456"]' in messages[0]
    assert '"job_ids": ["456", "999"]' in messages[1]
    assert not executor.executed and not Path(request.notebook).exists()
