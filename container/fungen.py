"""Portable first-run setup and the saved-config server/agent entrypoints."""

import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

SIZES = {"q4_K_M": 96, "q8_0": 128, "q4_K_M-256k-t2": 96, "q8_0-256k-t2": 128}
ROOT = Path(__file__).resolve().parents[1]


def config_path():
    return Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "fungen/config.json"


def read_config():
    path = config_path()
    return json.loads(path.read_text()) if path.exists() else {}


def endpoint(value):
    value = value if "://" in value else "http://" + value
    parsed = urlparse(value)
    if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username or parsed.password or parsed.path not in {"", "/"}
            or parsed.query or parsed.fragment):
        raise ValueError("Use a local HTTP endpoint, for example http://127.0.0.1:11434")
    _ = parsed.port
    return value.rstrip("/")


def api(url, path, data=None, timeout=10):
    request = urllib.request.Request(url + path, data=json.dumps(data).encode() if data is not None else None,
                                     headers={"Content-Type": "application/json"})
    # Local inference must also work on clusters with an HTTP proxy in the environment.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=timeout) as response:
        result = json.load(response)
    if "error" in result:
        raise RuntimeError(result["error"])
    return result


def environment(config):
    env = dict(os.environ, OLLAMA_MODELS=config["models"], OLLAMA_HOST=config["endpoint"])
    for key, value in {"OLLAMA_CONTEXT_LENGTH": "32768", "OLLAMA_KEEP_ALIVE": "5m",
                       "OLLAMA_NUM_PARALLEL": "1", "OLLAMA_MAX_LOADED_MODELS": "1",
                       "OLLAMA_FLASH_ATTENTION": "1", "OLLAMA_KV_CACHE_TYPE": "q8_0"}.items():
        env.setdefault(key, value)
    env["CODEX_OSS_BASE_URL"] = config["endpoint"] + "/v1"
    env["CODEX_OLLAMA_MODEL"] = config["model"]
    # Isolate agent state from host credentials/configuration. No Codex config file
    # is needed: the single Fungen config drives the CLI and optional MCP connection.
    env["CODEX_HOME"] = str(config_path().parent / "codex")
    Path(env["CODEX_HOME"]).mkdir(parents=True, exist_ok=True, mode=0o700)
    return env


def check_folder(folder, download, size_gb):
    folder = folder.expanduser().resolve()
    if download:
        folder.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=folder):
            pass
        free = shutil.disk_usage(folder).free
        required = int((size_gb * 1.1 + 2) * 1e9)
        print(f"Model storage: {folder}; free space {free / 1e9:.1f} GB; download budget {required / 1e9:.1f} GB")
        if free < required:
            raise ValueError("Insufficient free space for this download (includes 10% headroom + 2 GB).")
    else:
        if not folder.is_dir() or not os.access(folder, os.R_OK | os.X_OK):
            raise ValueError("Existing model folder must be a readable directory.")
        print(f"Reusing {folder} ({shutil.disk_usage(folder).free / 1e9:.1f} GB free); read-only storage is supported.")
    return str(folder)


def start(config):
    """Reuse only a daemon started by this configuration; reject other listeners."""
    state = config_path().parent
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    runtime = state / "server.json"
    with (state / "server.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        running = json.loads(runtime.read_text()) if runtime.exists() else {}
        parsed = urlparse(config["endpoint"])
        host, port = parsed.hostname, parsed.port or 80
        with socket.socket(socket.AF_INET6 if ":" in host else socket.AF_INET) as sock:
            busy = sock.connect_ex((host, port)) == 0
        if busy:
            if running.get("models") != config["models"] or running.get("endpoint") != config["endpoint"]:
                raise RuntimeError("Endpoint is occupied by another server. Select a different --endpoint.")
            # Linux start-time token prevents stale PID metadata accepting an unrelated daemon.
            if not running.get("token") or process_token(running.get("pid")) != running["token"]:
                raise RuntimeError("Saved server is stale; select a free --endpoint.")
            api(config["endpoint"], "/api/tags")
            print(f"Reusing Ollama PID {running['pid']}")
            return None
        with (state / "ollama.log").open("a") as log:
            process = subprocess.Popen(["ollama", "serve"], env=environment(config),
                                       stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                       start_new_session=True)
        runtime.write_text(json.dumps({"pid": process.pid, "token": process_token(process.pid),
                                       "models": config["models"], "endpoint": config["endpoint"]}))
        for _ in range(120):
            if process.poll() is not None:
                raise RuntimeError(f"Ollama exited; inspect {state / 'ollama.log'}")
            try:
                api(config["endpoint"], "/api/tags", timeout=1)
                return process
            except (OSError, ValueError):
                time.sleep(1)
        raise RuntimeError(f"Ollama startup timed out; inspect {state / 'ollama.log'}")


def process_token(pid):
    try:
        return Path(f"/proc/{int(pid)}/stat").read_text().rsplit(")", 1)[1].split()[19]
    except (OSError, ValueError, TypeError):
        return None


def setup(args):
    previous = read_config()
    interactive = not args.non_interactive
    download = args.download
    if download is None:
        if not interactive:
            raise ValueError("Non-interactive setup requires --download yes or --download no.")
        download = ask("Download Laguna S? [yes/no] (default no): ", "no", {"yes", "no"})
    print("Laguna S tags (approximate disk/download size):")
    for tag, size in SIZES.items():
        print(f"  {tag}: {size} GB" + (" (256K context, 2 CPU threads; local preset)" if "256k" in tag else ""))
    tag = args.tag or previous.get("model", "laguna-s-2.1:q4_K_M").split(":", 1)[1]
    if interactive and args.tag is None:
        tag = ask(f"Which tag? (default {tag}): ", tag, SIZES)
    if tag not in SIZES:
        raise ValueError("Unsupported Laguna S tag.")
    folder = args.models_dir or previous.get("models", str(Path.home() / ".fungen/models"))
    if interactive and args.models_dir is None:
        folder = input(f"Model folder to download into or reuse (default {folder}): ").strip() or folder
    folder = check_folder(Path(folder), download == "yes", SIZES[tag])
    config = {"models": folder, "model": "laguna-s-2.1:" + tag,
              "endpoint": endpoint(args.endpoint or previous.get("endpoint", "http://127.0.0.1:11434"))}
    process = start(config)
    if download == "yes":
        base_model = config["model"].removesuffix("-256k-t2")
        subprocess.run(["ollama", "pull", base_model], env=environment(config), check=True)
        if base_model != config["model"]:
            # The registry publishes the quantizations; these aliases are staged
            # presets. Create the same preset locally after pulling its base.
            with tempfile.NamedTemporaryFile(mode="w", suffix=".Modelfile") as modelfile:
                modelfile.write(f"FROM {base_model}\nPARAMETER num_ctx 262144\nPARAMETER num_thread 2\n")
                modelfile.flush()
                subprocess.run(["ollama", "create", config["model"], "-f", modelfile.name],
                               env=environment(config), check=True)
    tags = api(config["endpoint"], "/api/tags")["models"]
    if not any(m["name"] == config["model"] for m in tags):
        raise ValueError(f"{config['model']} is absent from this folder. Choose an installed tag or --download yes.")
    answer = api(config["endpoint"], "/api/generate", {
        "model": config["model"], "prompt": "Reply with one short greeting.", "stream": False,
        "think": False, "options": {"num_ctx": 4096, "num_predict": 64}}, timeout=args.timeout)
    if not answer.get("done") or not answer.get("response", "").strip():
        raise RuntimeError("One-line inference test returned no answer.")
    # Commit setup only after real inference succeeds. Atomic replacement preserves
    # the prior working config if a download/test fails.
    path = config_path()
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
        json.dump(config, stream, indent=2)
        stream.write("\n")
        temporary = stream.name
    os.replace(temporary, path)
    print("Model answered: " + answer["response"].strip())
    print(f"Saved {path}")
    print("Next time, inside this container:\n  fungen-serve\n  fungen-agent --deployment /workspace/deployment.json")
    print("CLI: fungen-operator --help; skills: /opt/fungen-operator/skills")
    if args.stay:
        print("Ollama is ready. Keep this container running; open another shell for the operator.", flush=True)
        if process:
            process.wait()
        else:
            while process_token(json.loads((path.parent / "server.json").read_text())["pid"]):
                time.sleep(5)


def ask(prompt, default, choices):
    while True:
        value = input(prompt).strip() or default
        if value in choices:
            return value
        print("Choose one of: " + ", ".join(choices))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    p = subs.add_parser("setup")
    p.add_argument("--non-interactive", action="store_true")
    p.add_argument("--download", choices=["yes", "no"], default=os.environ.get("FUNGEN_DOWNLOAD"))
    p.add_argument("--tag", default=os.environ.get("FUNGEN_MODEL_TAG"))
    p.add_argument("--models-dir", default=os.environ.get("FUNGEN_MODELS_DIR"))
    p.add_argument("--endpoint", default=os.environ.get("FUNGEN_ENDPOINT"))
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--stay", action="store_true", help="Keep the default container process alive with Ollama")
    subs.add_parser("serve")
    p = subs.add_parser("agent")
    p.add_argument("--deployment", type=Path, help="Connect the operator MCP server for this mounted deployment")
    p.add_argument("args", nargs=argparse.REMAINDER, help="Codex arguments, following --")
    args = parser.parse_args(argv)
    if args.command == "setup":
        setup(args)
        return
    config = read_config()
    if not config:
        raise ValueError("Run fungen-setup first.")
    env = environment(config)
    if args.command == "serve":
        os.execvpe("ollama", ["ollama", "serve"], env)
    extra = args.args[1:] if args.args[:1] == ["--"] else args.args
    # Put provider flags on exec itself: Codex's interactive and exec parsers
    # own their model/provider options independently.
    prefix = ["codex", "exec"] if extra[:1] == ["exec"] else ["codex"]
    if len(prefix) == 2:
        extra = extra[1:]
    command = prefix + ["--oss", "--local-provider", "ollama", "--model", config["model"],
               "-c", 'sandbox_mode="workspace-write"', "-c", 'approval_policy="on-request"',
               "-c", "developer_instructions=" + json.dumps(
                   "Read /opt/fungen-operator/skills/fungen-operator/SKILL.md before workflow operation. "
                   "Use its fixed notebook actions and human scientific approval gate. "
                   "The deployment supplies external workflow/runtime paths. ")]
    if args.deployment:
        command += ["-c", 'mcp_servers.fungen.command="/opt/python/bin/fungen-operator"',
                    "-c", "mcp_servers.fungen.args=" + json.dumps(
                        ["serve", "--deployment", str(args.deployment.resolve())])]
    os.execvpe("codex", command + extra, env)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError, subprocess.CalledProcessError, EOFError) as exc:
        print(f"fungen: {exc}", file=sys.stderr)
        sys.exit(1)
