"""Local entrypoints share the MCP harness; execute/replay are reviewed host commands."""

import argparse
import json
from pathlib import Path

from .actions import Deployment, MODELS, InspectRun
from .execution import Executor
from .harness import Harness
from .notebook import Notebook, verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    for name in ("serve", "execute", "replay", "inspect"):
        p = subs.add_parser(name)
        p.add_argument("--deployment", required=True)
        if name != "serve":
            p.add_argument("--notebook", required=True)
        if name == "execute":
            p.add_argument("--cell", required=True)
    action = subs.add_parser("action", help="Stage a typed action through the shared harness")
    action.add_argument("--deployment", required=True)
    action.add_argument("--action", choices=list(MODELS), required=True)
    action.add_argument("--request", required=True, help="JSON request file")
    check = subs.add_parser("verify")
    check.add_argument("notebook")
    check.add_argument("--deployment", help="Validate against a deployment file at any path")
    subs.add_parser("schemas")
    demo = subs.add_parser("demo")
    demo.add_argument("--root", required=True)
    args = parser.parse_args()
    if args.command == "schemas":
        print(json.dumps({k: v.model_json_schema() for k, v in {**MODELS, "inspect_run": InspectRun}.items()}, indent=2))
        return
    if args.command == "verify":
        if args.deployment:
            deployment = Deployment.model_validate_json(Path(args.deployment).read_text())
            deployment.validate_layout()
            deployment.validate_write_path(args.notebook)
        verify(Notebook(args.notebook).read())
        print("All active cells re-render identically.")
        return
    if args.command == "demo":
        from .demo import run_demo
        print(json.dumps(run_demo(Path(args.root).resolve()), indent=2))
        return
    deployment = Deployment.model_validate_json(Path(args.deployment).read_text())
    # These commands must themselves be launched through host approval on Minerva.
    executor = Executor(deployment, host_approved=args.command in {"execute", "replay", "inspect"},
                        host_inspection=args.command == "serve")
    harness = Harness(deployment, executor, str(Path(args.deployment).resolve()))
    if args.command == "action":
        request = MODELS[args.action].model_validate_json(Path(args.request).read_text())
        if args.action == "prepare_config":
            result = harness.prepare_config(harness.propose_config(request))
        else:
            result = harness.run(args.action, request)
        print(json.dumps(result, indent=2))
    elif args.command == "serve":
        from .server import serve_stdio
        serve_stdio(harness)
    elif args.command == "execute":
        print(json.dumps(harness.execute_pending(args.notebook, args.cell), indent=2))
    elif args.command == "replay":
        print(json.dumps(harness.replay(args.notebook), indent=2))
    else:
        print(json.dumps(harness.inspect(InspectRun(notebook=args.notebook)), indent=2))


if __name__ == "__main__":
    main()
