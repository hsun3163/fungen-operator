import asyncio
import json
import sys
from types import SimpleNamespace

import pytest
from mcp import Client

from fungen_operator.server import create_server


@pytest.mark.parametrize("backend", ["lsf", "sge", "slurm"])
def test_cluster_inspection_returns_reviewed_host_command_without_blocking(backend):
    """A large history must not consume the MCP transport's 300-second budget."""
    def slow_inspection(_request):
        pytest.fail("cluster inspection ran synchronously inside the MCP request")

    harness = SimpleNamespace(
        deployment=SimpleNamespace(backend=backend),
        deployment_file="/tmp/operator deployment.json",
        registry=SimpleNamespace(specs={}),
        inspect=slow_inspection,
    )
    request = {
        "notebook": "/tmp/operator-notebook.ipynb",
        "paths": ["/tmp/first-output.txt", "/tmp/second.txt"],
        "max_bytes": 731,
        "dead_child_grace_minutes": 19,
    }

    async def exercise():
        async with Client(create_server(harness), read_timeout_seconds=5) as client:
            result = await client.call_tool("inspect_run", {"request": request})
            assert not result.is_error, result
            data = result.structured_content
            assert data["status"] == "host_approval_required"
            assert data["host_command"] == [
                sys.executable, "-m", "fungen_operator", "inspect",
                "--deployment", harness.deployment_file,
                "--notebook", request["notebook"],
                "--max-bytes", "731", "--dead-child-grace-minutes", "19",
                "--path", request["paths"][0], "--path", request["paths"][1],
            ]

    asyncio.run(exercise())


def test_host_inspection_cli_preserves_the_structured_request(monkeypatch, capsys):
    from fungen_operator import __main__ as cli

    deployment = SimpleNamespace()
    captured = {}
    monkeypatch.setattr(cli.Deployment, "load", lambda path: deployment)
    monkeypatch.setattr(cli, "Executor", lambda dep, **kw: None)

    class HostHarness:
        def __init__(self, *_args):
            pass

        def inspect(self, request):
            captured.update(request.model_dump())
            return {"inspection_status": "verified"}

    monkeypatch.setattr(cli, "Harness", HostHarness)
    monkeypatch.setattr(sys, "argv", [
        "fungen-operator", "inspect", "--deployment", "/tmp/deployment.json",
        "--notebook", "/tmp/operator.ipynb", "--max-bytes", "731",
        "--dead-child-grace-minutes", "19", "--path", "/tmp/first-output.txt",
        "--path", "/tmp/second.txt",
    ])
    cli.main()
    assert captured == {
        "notebook": "/tmp/operator.ipynb",
        "paths": ["/tmp/first-output.txt", "/tmp/second.txt"],
        "max_bytes": 731,
        "dead_child_grace_minutes": 19,
    }
    assert json.loads(capsys.readouterr().out)["inspection_status"] == "verified"
