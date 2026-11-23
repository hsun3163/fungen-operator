"""Execution controls preserve retained cells and remain visible native arguments."""

import hashlib

import pytest
from pydantic import ValidationError

from fungen_operator.actions import CheckReadiness, InitiateRun, render


@pytest.fixture
def slots():
    root = "/tmp/fungen-sos-settings"
    return {"arguments": dict(notebook=f"{root}/run/operator.ipynb",
        configfile=f"{root}/run/config.yml", workdir=f"{root}/run/work",
        log_dir=f"{root}/run/logs", targets=["all"], jobs=100),
        "bindings": dict(snakefile=f"{root}/source/workflow/snakefile_combined.py",
        profile_path=f"{root}/source/profile", conda_sh=f"{root}/conda.sh",
        conda_env=f"{root}/env", log_stem=f"{root}/run/logs/attempt")}


@pytest.mark.parametrize("model", [CheckReadiness, InitiateRun])
def test_execution_defaults_and_upper_bounds(slots, model):
    args = dict(slots["arguments"])
    args.pop("jobs")
    assert model(**args).jobs == 2000
    assert model(**args, jobs=10000).jobs == 10000


@pytest.mark.parametrize("field", ["jobs"])
@pytest.mark.parametrize("value", [0, 10001, True, "100"])
def test_typed_execution_bounds(slots, field, value):
    args = {**slots["arguments"], field: value}
    with pytest.raises(ValidationError):
        InitiateRun(**args)


def test_sos_queue_is_typed(slots):
    with pytest.raises(ValidationError):
        InitiateRun(**slots["arguments"], sos_queue="express;id")


@pytest.mark.parametrize("action,expected", [
    ("initiate_run", "2e1c4293c90fae1ab5b4aba487b51d97c4934dd6dd936e8e297077f7a75be57f"),
    ("check_readiness", "b89e671dd2d14104eda2de97d837c2de75aba20b50de528d2df65d518553eefd"),
])
def test_omitted_settings_keep_legacy_cell_bytes(slots, action, expected):
    # Frozen from the pre-feature renderer with the retained explicit jobs value.
    source = render(action, slots)
    assert hashlib.sha256(source.encode()).hexdigest() == expected


@pytest.mark.parametrize("field,value", [("sos_j",10000),("sos_max_running_jobs",10000),("sos_queue","express")])
def test_sos_request_slots_are_retired(slots, field, value):
    with pytest.raises(ValidationError):
        InitiateRun(**slots["arguments"], **{field:value})
