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
    values = model(**args, jobs=10000, sos_j=10000, sos_max_running_jobs=10000,
                   sos_queue="express")
    assert values.sos_j == values.sos_max_running_jobs == values.jobs == 10000
    assert model(**args).sos_queue is None


@pytest.mark.parametrize("field", ["jobs", "sos_j", "sos_max_running_jobs"])
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
    slots["arguments"].update(sos_j=None, sos_max_running_jobs=None, sos_queue=None)
    assert render(action, slots) == source


@pytest.mark.parametrize("action", ["initiate_run", "check_readiness"])
def test_sos_settings_render_in_native_command(slots, action):
    slots["arguments"].update(sos_j=8000, sos_max_running_jobs=9000, sos_queue="premium")
    source = render(action, slots)
    assert ("  --config fungen_sos_j=8000 fungen_sos_max_running_jobs=9000 "
            "fungen_sos_queue=premium "
            "fungen_sos_config=/tmp/fungen-sos-settings/run/logs/attempt.sos.yml \\\n") in source
    assert "python -m snakemake" in source
    assert "--configfile /tmp/fungen-sos-settings/run/config.yml" in source
