"""Typed native bmod commands retain approved resources and run membership."""
from pathlib import Path

import pytest
from pydantic import ValidationError

from fungen_operator.fixture import create_fixture
from fungen_operator.harness import Harness
from fungen_operator.live_control import ControlRun, Selector, commands, render_control, update_reservation


REQ = "select[type == any] order[r15s:pg] rusage[mem=56000.00:swp=1000] span[hosts=1]"


def request(**changes):
    return ControlRun(notebook="/tmp/operator.ipynb", operation="modify", job_ids=["123"], **changes)


@pytest.mark.parametrize("field,value,expected", [
    ("memory_limit_gb", 35, ["-M", "35G"]),
    ("walltime_minutes", 61, ["-W", "61"]),
    ("cores", 12, ["-n", "12"]),
    ("queue", "premium", ["-q", "premium"]),
    ("queue", "express", ["-q", "express"]),
])
def test_each_typed_bmod_field(field, value, expected):
    assert commands(request(**{field: value}), ["123"]) == [["bmod", *expected, "123"]]


def test_memory_reservation_preserves_all_other_native_constraints():
    updated = REQ.replace("mem=56000.00", "mem=34G")
    assert update_reservation(REQ, 34) == updated
    assert commands(request(memory_reservation_gb=34), ["123"], {"123": REQ}) == [
        ["bmod", "-R", updated, "123"]]


def test_all_modify_fields_are_visible_in_a_fixed_native_order():
    req = request(memory_reservation_gb=34, memory_limit_gb=35, walltime_minutes=240, cores=8, queue="premium")
    argv = commands(req, ["123"], {"123": REQ})
    assert argv == [["bmod", "-R", update_reservation(REQ, 34),
                     "-M", "35G", "-W", "240", "-n", "8", "-q", "premium", "123"]]
    rendered = render_control({"arguments": req.model_dump(),
        "bindings": {"job_ids": ["123"], "resource_requirements": {"123": REQ}}})
    assert rendered.startswith("%%bash\nset -eo pipefail\nbmod -R '")
    assert rendered.endswith("-M 35G -W 240 -n 8 -q premium 123\n")


def test_modify_groups_only_identical_preserved_requirements():
    other = REQ.replace("hosts=1", "hosts=2")
    argv = commands(request(memory_reservation_gb=34), ["123", "456", "789"],
        {"123": REQ, "456": other, "789": REQ})
    assert argv == [["bmod", "-R", update_reservation(REQ, 34), "123", "789"],
                    ["bmod", "-R", update_reservation(other, 34), "456"]]
    rendered = render_control({"arguments": request(memory_reservation_gb=34).model_dump(),
        "bindings": {"job_ids": ["123", "456"], "resource_requirements": {"123": REQ, "456": other}}})
    assert rendered.count("\nbmod ") == 2


@pytest.mark.parametrize("requirements", [None, {}, {"123": REQ, "456": REQ}, {"123": ""}, {"123": None}])
def test_memory_modification_requires_exact_native_binding(requirements):
    with pytest.raises(ValueError):
        commands(request(memory_reservation_gb=34), ["123"], requirements)


@pytest.mark.parametrize("requirement", ["", "span[hosts=1]", "rusage[swp=1000]", "rusage[mem=all]",
    "rusage[mem=56000] rusage[mem=75000]", "rusage[mem=56000:mem=75000]",
    "rusage[mem=56000:mem=unknown]", "rusage[mem=56000]\nspan[hosts=1]"])
def test_ambiguous_resource_requirements_require_explicit_review(requirement):
    with pytest.raises(ValueError):
        update_reservation(requirement, 34)


@pytest.mark.parametrize("field,values", [
    ("memory_reservation_gb", [0, 1001, True, 1.0, "34"]),
    ("memory_limit_gb", [0, 1001, True, 1.0, "35"]),
    ("walltime_minutes", [0, 8641, True, 1.0, "60"]),
    ("cores", [0, 513, True, 1.0, "8"]),
    ("queue", ["other", True, 1]),
])
def test_modify_field_types_and_bounds(field, values):
    for value in values:
        with pytest.raises(ValidationError):
            request(**{field: value})


@pytest.mark.parametrize("field,minimum,maximum", [
    ("memory_reservation_gb", 1, 1000), ("memory_limit_gb", 1, 1000),
    ("walltime_minutes", 1, 8640), ("cores", 1, 512)])
def test_modify_inclusive_bounds(field, minimum, maximum):
    assert getattr(request(**{field: minimum}), field) == minimum
    assert getattr(request(**{field: maximum}), field) == maximum


def test_modify_requires_a_setting_and_other_operations_reject_resources():
    with pytest.raises(ValidationError, match="at least one"):
        request()
    for operation in ("kill", "switch_queue"):
        with pytest.raises(ValidationError, match="only modify"):
            ControlRun(notebook="/tmp/operator.ipynb", operation=operation, job_ids=["123"],
                       memory_limit_gb=35, queue="premium" if operation == "switch_queue" else None)
    with pytest.raises(ValidationError):
        request(unknown_setting=1)


def test_step_selector_requires_typed_current_memory_and_exact_step():
    selector = Selector(kind="step", step="otters_weights", memory_reservation_gb=75)
    assert selector.step == "otters_weights" and selector.memory_reservation_gb == 75
    for values in ({"step": "otters_weights"}, {"memory_reservation_gb": 75},
                   {"step": "x;id", "memory_reservation_gb": 75},
                   {"step": "x", "memory_reservation_gb": True},
                   {"step": "x", "memory_reservation_gb": 75, "queue": "express"}):
        with pytest.raises(ValidationError):
            Selector(kind="step", **values)
    with pytest.raises(ValidationError):
        Selector(kind="pending", queue="express", min_pending_minutes=10, step="x")


@pytest.mark.parametrize("operation,queue,literal", [
    ("kill", None, "bkill 123"), ("switch_queue", "premium", "bswitch premium 123")])
def test_legacy_control_renders_remain_identical(operation, queue, literal):
    old_arguments = {"notebook": "/tmp/operator.ipynb", "operation": operation,
                     "job_ids": ["123"], "selector": None, "queue": queue, "dead_child_grace_minutes": 10}
    assert render_control({"arguments": old_arguments, "bindings": {"job_ids": ["123"]}}) == (
        "%%bash\nset -eo pipefail\n" + literal + "\n")


@pytest.mark.parametrize("changes", [{"memory_reservation_gb": 34}, {"memory_limit_gb": 35},
    {"walltime_minutes": 60}, {"cores": 8}, {"queue": "premium"}])
def test_modify_outside_membership_refuses_before_any_command(tmp_path, monkeypatch, changes):
    deployment = create_fixture(tmp_path / "fixture")
    notebook = str(Path(deployment.run_root, "operator.ipynb"))
    class NoExecution:
        can_inspect = True
        can_schedule = True
        def execute(self, *args):
            pytest.fail("outside-run modification reached execution")
    harness = Harness(deployment, NoExecution())
    monkeypatch.setattr(harness, "_job_snapshot", lambda *args: {"scheduler_ok": True, "jobs": {
        "789": {"membership": False, "status": "RUN", "membership_reason": "job is outside this run"}}})
    result = harness.propose_control(ControlRun(notebook=notebook, operation="modify", job_ids=["789"], **changes))
    assert result["status"] == "refused"
    assert result["refusals"] == [{"job_id": "789", "reason": "job is outside this run"}]
    assert not Path(notebook).exists()
