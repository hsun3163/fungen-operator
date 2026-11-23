"""Explicitly synthetic scheduler/workflow commands, used only by tests and demo.

These stand in for external LSF/Snakemake, not for rendering or notebook execution.
No real scheduler client or workflow engine is called.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

def create_fixture(root: Path):
    import yaml
    from .actions import Deployment

    root = root.resolve()
    if root.exists() and any(root.iterdir()):
        raise ValueError(f"fixture root must be new or empty: {root}")
    repository, runtime, runs = root / "canonical", root / "runtime", root / "runs"
    for p in (repository, runtime / "bin", runs, repository / "profile"):
        p.mkdir(parents=True, exist_ok=True)
    config = {"cwd": str(runs / "work"), "pca": {"n_pcs": 20},
              "resources": {"default": {"threads": 1, "mem_mb": 40960, "runtime": 60}},
              "outputs": ["output/result.txt", "output/result.index"]}
    (repository / "config.yaml").write_text(yaml.safe_dump(config))
    (repository / "Snakefile").write_text(
        '# Synthetic fixture contract. External commands are simulated.\n'
        'rule all:\n    input: config["outputs"]\n'
        'rule artifact:\n    output: "output/{name}"\n    shell: "echo synthetic > {output}"\n')
    (repository / "profile/config.yaml").write_text("executor: lsf\nrerun-incomplete: true\n")
    (runtime / "conda.sh").write_text("# Synthetic activation; never activates a production runtime.\nconda() { :; }\n")
    for program in ("bsub", "bjobs", "python"):
        p = runtime / "bin" / program
        p.write_text(f"#!{sys.executable}\nimport sys\nsys.path.insert(0, {str(Path(__file__).resolve().parents[1])!r})\n"
                     f"from fungen_operator.fixture import main\nmain({program!r})\n")
        p.chmod(0o755)
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repository), "-c", "user.name=Fungen fixture", "-c",
                    "user.email=fixture@example.invalid", "commit", "-qm", "Synthetic canonical fixture"], check=True)
    deployment = Deployment(repository=str(repository), snakefile=str(repository / "Snakefile"),
                            default_config=str(repository / "config.yaml"), profile_path=str(repository / "profile"),
                            conda_sh=str(runtime / "conda.sh"), conda_env=str(runtime),
                            run_root=str(runs), backend="fixture")
    (root / "deployment.json").write_text(deployment.model_dump_json(indent=2))
    return deployment


def main(program):
    root = Path(os.environ["FUNGEN_FIXTURE_ROOT"])
    state_path = root / "scheduler.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    if program == "bjobs":
        record = state.get(sys.argv[-1])
        print(json.dumps({"RECORDS": [record] if record else []}))
        return
    if program == "bsub":
        script = sys.stdin.read()
        job = str(1001 + len(state))
        paths = {}
        for option, stream in (("oo", "stdout"), ("eo", "stderr")):
            match = re.search(rf"(?m)^#BSUB -{option} (\S+)$", script)
            paths[stream] = Path(match.group(1).replace("%J", job))
        with paths["stdout"].open("w") as out, paths["stderr"].open("w") as err:
            result = subprocess.run(["bash"], input=script, text=True, stdout=out, stderr=err)
        state[job] = {"JOBID": job, "STAT": "DONE" if result.returncode == 0 else "EXIT",
                      "EXIT_CODE": str(result.returncode)}
        state_path.write_text(json.dumps(state))
        print(f"Job <{job}> is submitted to queue <premium>.")
        if "-K" in sys.argv:
            print("<<Job is finished>>")
            sys.exit(result.returncode)
        return
    if sys.argv[1:3] != ["-m", "snakemake"]:
        raise RuntimeError("fixture python supports only the rendered Snakemake command")
    parser = argparse.ArgumentParser()
    for name in ("snakefile", "configfile", "profile", "cores", "jobs", "latency-wait"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--printshellcmds", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("targets", nargs="+")
    args = parser.parse_args(sys.argv[3:])
    import yaml
    config_text = Path(args.configfile).read_text()
    cfg = yaml.safe_load(config_text)
    targets = [Path(p) for p in (cfg["outputs"] if args.targets == ["all"] else args.targets)]
    signature = "SYNTHETIC fixture output; config=" + hashlib.sha256(config_text.encode()).hexdigest() + "\n"
    pending = [p for p in targets if not p.exists() or p.read_text() != signature]
    if args.dry_run:
        print("SYNTHETIC scheduler/workflow backend")
        if not pending:
            print("Nothing to be done (all requested files are present and up to date).")
        else:
            print(f"Job stats:\nartifact {len(pending)}\nThis was a dry-run (flag -n).")
        return
    interrupt = root / "interrupt-next"
    for target in pending:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(signature)
        print(f"SYNTHETIC produced {target}")
        if interrupt.exists():
            interrupt.unlink()
            print("SYNTHETIC controller interruption after first output", file=sys.stderr)
            sys.exit(17)
    print("SYNTHETIC workflow finished")
