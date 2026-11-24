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
        if name == "inspect":
            p.add_argument("--path", action="append", default=[])
            p.add_argument("--max-bytes", type=int, default=10000)
            p.add_argument("--dead-child-grace-minutes", type=int, default=10)
    action = subs.add_parser("action", help="Stage a typed action through the shared harness")
    action.add_argument("--deployment", required=True)
    action.add_argument("--action", required=True)
    action.add_argument("--request", required=True, help="JSON request file")
    check = subs.add_parser("verify")
    check.add_argument("notebook")
    check.add_argument("--deployment", help="Validate against a deployment file at any path")
    sup = subs.add_parser("supervise", help="One supervision pass over assigned runs (host command)")
    sup.add_argument("--deployment", required=True)
    sup.add_argument("--state", required=True, help="Supervision JSON state file inside the run root")
    mode = sup.add_mutually_exclusive_group()
    mode.add_argument("--assign", metavar="NOTEBOOK", help="Watch this notebook's run instead of checking")
    mode.add_argument("--watching", action="store_true", help="Exit 0 if any run is watched, else 3")
    sup.add_argument("--max-attempts", type=int, default=3, help="With --assign: recoveries allowed")
    sup.add_argument("--max-walltime-minutes", type=int,
                     help="With --assign: highest controller walltime a recovery may request")
    schemas = subs.add_parser("schemas")
    schemas.add_argument("--deployment", help="Include actions from this deployment provider")
    demo = subs.add_parser("demo")
    demo.add_argument("--root", required=True)
    args = parser.parse_args()
    if args.command == "schemas":
        models = Deployment.load(args.deployment).registry.models if args.deployment else MODELS
        print(json.dumps({k: v.model_json_schema() for k, v in {**models, "inspect_run": InspectRun}.items()}, indent=2))
        return
    if args.command == "verify":
        if args.deployment:
            deployment = Deployment.load(args.deployment)
            deployment.validate_layout()
            deployment.validate_write_path(args.notebook)
        registry = deployment.registry if args.deployment else None
        Notebook(args.notebook, registry).read()
        print("All active cells re-render identically.")
        return
    if args.command == "demo":
        from .demo import run_demo
        print(json.dumps(run_demo(Path(args.root).resolve()), indent=2))
        return
    if args.command == "supervise":
        from . import supervise
        if args.watching:
            raise SystemExit(0 if supervise.watching(args.state) else supervise.EXIT_NOTHING_WATCHED)
        deployment = Deployment.load(args.deployment)
        if args.assign:
            print(json.dumps(supervise.assign(deployment, args.state, args.assign,
                                              max_attempts=args.max_attempts,
                                              max_walltime_minutes=args.max_walltime_minutes), indent=2))
            return
        # A pass is itself a host command, like execute and replay.
        harness = Harness(deployment, Executor(deployment, host_approved=True), str(Path(args.deployment).resolve()))
        code, decisions = supervise.supervise(harness, args.state)
        print(json.dumps({"time": supervise.now(), "decisions": decisions}, indent=2))
        raise SystemExit(code)
    deployment = Deployment.load(args.deployment)
    # These commands must themselves be launched through host approval on Minerva.
    executor = Executor(deployment, host_approved=args.command in {"execute", "replay", "inspect"},
                        host_inspection=args.command == "serve")
    harness = Harness(deployment, executor, str(Path(args.deployment).resolve()))
    if args.command == "action":
        request = harness.registry.models[args.action].model_validate_json(Path(args.request).read_text())
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
        result=harness.inspect(InspectRun(notebook=args.notebook, paths=args.path,
                                        max_bytes=args.max_bytes,
                                        dead_child_grace_minutes=args.dead_child_grace_minutes))
        print(json.dumps(result, indent=2))
        if result.get('inspection_status')=='not_verified':raise SystemExit(1)


if __name__ == "__main__":
    main()
