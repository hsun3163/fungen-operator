"""Bounded setup regressions, requiring no model download or daemon."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

spec = importlib.util.spec_from_file_location("fungen_setup", Path(__file__).with_name("fungen.py"))
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


@pytest.mark.parametrize("value", ["http://other:11434", "https://localhost", "http://localhost/v1", "http://u:p@localhost"])
def test_endpoint_rejects_nonlocal_or_ambiguous(value):
    with pytest.raises(ValueError):
        setup.endpoint(value)


def test_folder_space_gate(tmp_path, monkeypatch):
    monkeypatch.setattr(setup.shutil, "disk_usage", lambda _: SimpleNamespace(free=1))
    with pytest.raises(ValueError, match="Insufficient"):
        setup.check_folder(tmp_path, True, 96)
    assert setup.check_folder(tmp_path, False, 96) == str(tmp_path)


def test_reuse_does_not_write_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(setup.tempfile, "TemporaryFile", Mock(side_effect=AssertionError("write")))
    assert setup.check_folder(tmp_path, False, 96) == str(tmp_path)


def test_noninteractive_requires_download_choice(monkeypatch):
    monkeypatch.setattr(setup, "read_config", lambda: {})
    with pytest.raises(ValueError, match="requires --download"):
        setup.main(["setup", "--non-interactive"])


@pytest.mark.parametrize("answer,passes", [({"done": True, "response": "Hello"}, True),
                                         ({"done": True, "response": ""}, False)])
def test_reuse_and_atomic_config(tmp_path, monkeypatch, answer, passes):
    config = tmp_path / "config/config.json"
    config.parent.mkdir()
    config.write_text('{"original": true}')
    monkeypatch.setattr(setup, "config_path", lambda: config)
    monkeypatch.setattr(setup, "start", lambda _: None)
    monkeypatch.setattr(setup, "api", lambda _, path, *a, **kw: (
        {"models": [{"name": "laguna-s-2.1:q4_K_M"}]} if path == "/api/tags" else answer))
    args = ["setup", "--non-interactive", "--download", "no", "--models-dir", str(tmp_path)]
    if passes:
        setup.main(args)
        assert json.loads(config.read_text())["models"] == str(tmp_path)
        setup.main(args)
    else:
        with pytest.raises(RuntimeError, match="no answer"):
            setup.main(args)
        assert json.loads(config.read_text()) == {"original": True}


def test_interactive_no_download_prompts(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(setup, "read_config", lambda: {})
    answers = iter(["no", "", str(tmp_path)])
    def respond(prompt):
        print(prompt)
        return next(answers)
    monkeypatch.setattr("builtins.input", respond)
    monkeypatch.setattr(setup, "start", Mock(side_effect=RuntimeError("stop before daemon")))
    with pytest.raises(RuntimeError, match="stop before"):
        setup.main(["setup"])
    output = capsys.readouterr().out
    assert "Download Laguna S?" in output and "Which tag?" in output and "Model folder" in output


def test_preset_pulls_library_base_then_creates_alias(tmp_path, monkeypatch):
    config = tmp_path / "config.json"
    monkeypatch.setattr(setup, "config_path", lambda: config)
    monkeypatch.setattr(setup, "check_folder", lambda *a: str(tmp_path))
    monkeypatch.setattr(setup, "start", lambda _: None)
    monkeypatch.setattr(setup, "environment", lambda _: {})
    calls = Mock()
    monkeypatch.setattr(setup.subprocess, "run", calls)
    monkeypatch.setattr(setup, "api", lambda _, path, *a, **kw: (
        {"models": [{"name": "laguna-s-2.1:q4_K_M-256k-t2"}]} if path == "/api/tags" else
        {"done": True, "response": "Hello"}))
    setup.main(["setup", "--non-interactive", "--download", "yes", "--tag", "q4_K_M-256k-t2"])
    assert calls.call_args_list[0].args[0] == ["ollama", "pull", "laguna-s-2.1:q4_K_M"]
    assert calls.call_args_list[1].args[0][:3] == ["ollama", "create", "laguna-s-2.1:q4_K_M-256k-t2"]


def test_agent_exec_selects_saved_local_provider(monkeypatch):
    config = {"models": "/models", "model": "laguna-s-2.1:q4_K_M", "endpoint": "http://127.0.0.1:11434"}
    monkeypatch.setattr(setup, "read_config", lambda: config)
    monkeypatch.setattr(setup, "environment", lambda _: {"CODEX_OLLAMA_MODEL": config["model"]})
    captured = []
    monkeypatch.setattr(setup.os, "execvpe", lambda *args: captured.append(args))
    setup.main(["agent", "--", "exec", "--ephemeral", "hello"])
    _, command, env = captured[0]
    assert command[:3] == ["codex", "exec", "--oss"]
    assert command[command.index("--model") + 1] == config["model"]
    assert env["CODEX_OLLAMA_MODEL"] == config["model"]
