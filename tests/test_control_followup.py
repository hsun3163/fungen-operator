"""The follow-up operations share exact-command approval and native receipts."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp import Client
from mcp.types import ElicitResult

from fungen_operator.actions import render
from fungen_operator.live_control import ControlRun
from fungen_operator.notebook import Notebook, active, verify
from fungen_operator.server import create_server
from fungen_operator.sweep_cell import sweep_result
from test_live_control import control, proof


def sweep_request(request):
    return ControlRun(notebook=request.notebook, operation="sweep", sweep={
        "memory_remaps": [{"step": "univariate_rss", "from_gb": 56, "to_gb": 34}],
        "queue_move": {"from_queue": "express", "to_queue": "premium", "limit": 1000},
        "interval_seconds": 0})


def test_modify_uses_step_memory_selector_and_exact_resource_approval(control):
    h, executor, request, snapshot = control
    snapshot["jobs"]["123"].update(rule="univariate_rss_gwas", task_kind="univariate_rss",
        memory_reservation_gb=56, combined_resreq="select[mem>0] rusage[mem=57344] span[hosts=1]")
    request = ControlRun(notebook=request.notebook, operation="modify", memory_reservation_gb=34,
                         selector={"kind": "step", "step": "univariate_rss", "memory_reservation_gb": 56})
    proposal = h.propose_control(request)
    assert proposal["job_ids"] == ["123"]
    assert proposal["commands"] == [["bmod", "-R", "select[mem>0] rusage[mem=34G] span[hosts=1]", "123"]]
    snapshot["jobs"]["123"]["combined_resreq"] = "rusage[mem=57344] span[hosts=2]"
    with pytest.raises(ValueError, match="changed"):
        h.control_run(proposal, proof(proposal))
    assert not executor.executed


@pytest.mark.parametrize("answer", ["accept", "decline", "cancel"])
def test_sweep_approval_binds_rules_cap_interval_and_visible_cell(control, answer):
    h, executor, request, _ = control
    request = sweep_request(request)
    executor.can_schedule = False
    asked = []
    async def respond(ctx, params):
        asked.append(params.message)
        assert "bsub -K" in params.message
        assert '"limit": 1000' in params.message and '"interval_seconds": 0' in params.message
        return ElicitResult(action=answer, content={"approve": True} if answer == "accept" else None)
    async def exercise():
        async with Client(create_server(h), mode="2026-07-28", elicitation_callback=respond) as client:
            response = await client.call_tool("control_run", {"request": request.model_dump()})
            assert not response.is_error, response
            assert response.structured_content["status"] == ("host_approval_required" if answer == "accept" else "approval_declined")
    asyncio.run(exercise())
    assert len(asked) == 1 and not executor.executed
    if answer == "accept":
        nb = Notebook(request.notebook).read()
        cell = active(nb)[0]
        assert "-m fungen_operator.sweep --plan" in cell.source
        assert "#BSUB -M 4GB" in cell.source
        assert cell.metadata.fungen.approval.channel == "mcp_human_elicitation"
        assert not Path(cell.metadata.fungen.slots.bindings.plan_path).exists()
        verify(nb)
    else:
        assert not Path(request.notebook).exists()


def test_one_pass_receipt_waits_for_same_terminal_scheduler_record(control, monkeypatch):
    h, _, request, _ = control
    request = sweep_request(request)
    proposal = h.propose_control(request)
    bindings = SimpleNamespace(**proposal["bindings"])
    plan = json.loads(bindings.plan_text)
    path = Path(plan["log_path"]); path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"scheduler_ok": True, "memory_changed": 0, "queue_changed": 0,
                                "active_jobs": 0, "failures": 0}) + "\n")
    states = iter([{"status": "RUN"}, {"status": "DONE"}])
    executor = SimpleNamespace(scheduler=lambda job: next(states), logs=lambda stem,job: {"stdout": "complete"})
    monkeypatch.setattr("time.sleep", lambda delay: None)
    result = sweep_result(executor, request, bindings, "Job <321> is submitted to queue <premium>.\n", False, {})
    assert result["status"] == "completed" and result["job_id"] == "321"
    assert result["last_pass"]["memory_changed"] == result["last_pass"]["queue_changed"] == 0


def test_control_approval_keeps_raw_legacy_arguments(control):
    h, _, request, _ = control
    proposal = h.propose_control(request)
    for key in ["memory_reservation_gb", "memory_limit_gb", "walltime_minutes", "cores", "sweep"]:
        proposal["arguments"].pop(key, None)
    from fungen_operator.live_control import approval_fingerprint
    proposal["fingerprint"] = approval_fingerprint(proposal["arguments"], proposal["bindings"])
    result = h.control_run(proposal, proof(proposal))
    cell = active(Notebook(request.notebook).read())[0]
    h.validate_control_cell(Notebook(request.notebook).read(), cell)
    assert result["status"] == "controlled"
