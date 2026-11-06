#!/usr/bin/env python3
"""Publish SIF tags to GHCR and verify manifests, tag listings and pulled bytes.

Example (run on a network-capable host, outside the Minerva sandbox):
  python3 container/publish.py image.sif ollama0.40.6-codex0.155.1 latest
Credentials: GHCR_TOKEN, otherwise `gh auth token`. Never pass tokens as arguments.
Singularity/Apptainer stores the login in its normal credential store.
"""
import argparse
import base64
import hashlib
import io
from email.parser import Parser
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse

FIX = ("Owner action: export GHCR_TOKEN from a classic PAT with write:packages and "
       "read:packages and access to this package, then rerun this command. "
       "Alternatively, the owner can complete `gh auth refresh -h github.com "
       "-s write:packages,read:packages` in their own browser, then rerun. "
       "This script never starts device sign-in.")
if os.environ.get("GITHUB_ACTIONS") == "true":
    FIX = ("Owner action: open the GHCR package Settings > Manage Actions access, "
           "add " + os.environ.get("GITHUB_REPOSITORY", "the workflow repository") +
           " with Write permission, retain workflow permissions packages: write, "
           "then rerun this workflow. Keep the package private. "
           "GITHUB_TOKEN requires access to this existing package; no personal-token secret is required.")
ACCEPT = "application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json"


class Response(io.BytesIO):
    def __init__(self, body, headers):
        super().__init__(body)
        self.headers = headers


def request(url, authorization, accept="application/json"):
    # curl follows the same HTTPS proxy path used by gh on Minerva. Secrets go
    # through stdin, never command arguments, disk, or diagnostic output.
    config = "\n".join(f"{key} = {json.dumps(value)}" for key, value in (
        ("url", url), ("header", "Authorization: " + authorization),
        ("header", "Accept: " + accept), ("user-agent", "fungen-sif-publisher")))
    with tempfile.TemporaryDirectory(prefix="fungen-registry-") as directory:
        headers = Path(directory) / "headers"
        body = Path(directory) / "body"
        result = subprocess.run(["curl", "--silent", "--show-error", "--fail",
                                 "--connect-timeout", "30", "--max-time", "120",
                                 "--dump-header", str(headers), "--output", str(body),
                                 "--write-out", "%{http_code}", "--config", "-"],
                                input=config + "\n", text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError(f"Registry/API request failed: curl exit {result.returncode}, "
                               f"HTTP {result.stdout.strip()}. " + FIX)
        # Proxy CONNECT may prepend a header block. Use the final HTTP response.
        final_headers = headers.read_text().strip().split("\n\n")[-1].split("\n", 1)[1]
        return Response(body.read_bytes(), Parser().parsestr(final_headers))


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def bearer(repository, username, token, actions):
    query = urllib.parse.urlencode({"service": "ghcr.io", "scope": f"repository:{repository}:{actions}"})
    basic = base64.b64encode(f"{username}:{token}".encode()).decode()
    with request("https://ghcr.io/token?" + query, "Basic " + basic) as response:
        body = json.load(response)
    return "Bearer " + (body.get("token") or body["access_token"])


def verify(repository, tag, username, token, source_sha):
    authorization = bearer(repository, username, token, "pull")
    base = f"https://ghcr.io/v2/{repository}"
    with request(f"{base}/manifests/{tag}", authorization, ACCEPT) as response:
        raw = response.read()
        registry_digest = response.headers.get("Docker-Content-Digest")
    manifest_digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    if registry_digest != manifest_digest:
        raise RuntimeError(f"Manifest digest mismatch: {registry_digest} != {manifest_digest}")
    manifest = json.loads(raw)
    layers = manifest.get("layers", [])
    if len(layers) != 1 or layers[0].get("digest") != source_sha:
        raise RuntimeError("Registry SIF layer digest differs from the input SIF sha256")
    url = base + "/tags/list?n=100"
    while url:
        with request(url, authorization) as response:
            listing = json.load(response)
            link = response.headers.get("Link", "")
        if tag in (listing.get("tags") or []):
            break
        next_link = re.search(r'<([^>]+)>;\s*rel="next"', link)
        url = urllib.parse.urljoin(url, next_link[1]) if next_link else None
        if url and not url.startswith(base + "/tags/list?"):
            raise RuntimeError("Unexpected registry pagination destination")
    else:
        raise RuntimeError(f"Authenticated tag listing does not contain {tag}")
    return {"tag": tag, "manifest_digest": manifest_digest, "sif_sha256": source_sha}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sif", type=Path)
    parser.add_argument("tags", nargs="+")
    parser.add_argument("--repository", default="hsun3163/fungen-operator", help="GHCR namespace/name")
    parser.add_argument("--username", default=os.environ.get("GHCR_USERNAME", "hsun3163"))
    parser.add_argument("--runtime", default=shutil.which("singularity") or shutil.which("apptainer"))
    parser.add_argument("--output", type=Path, default=Path("publish.json"))
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._/-]*", args.repository):
        parser.error("repository must be a lowercase GHCR namespace/name")
    tags = list(dict.fromkeys(args.tags))
    if any(not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", tag) for tag in tags):
        parser.error("invalid OCI tag")
    if not args.sif.is_file() or not args.runtime:
        parser.error("an existing SIF and singularity/apptainer runtime are required")
    if args.output.exists():
        parser.error("use a new --output path to preserve existing publication evidence")
    token = os.environ.get("GHCR_TOKEN")
    if not token:
        token = subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    if not token:
        raise RuntimeError("GHCR_TOKEN or an authenticated gh token is required. " + FIX)
    # OAuth/classic PAT scopes are explicit in this header. GITHUB_TOKEN has no
    # OAuth scope header; its packages permission is enforced by the registry.
    with request("https://api.github.com/rate_limit", "Bearer " + token) as response:
        scopes = response.headers.get("X-OAuth-Scopes")
    if scopes is not None and "write:packages" not in {s.strip() for s in scopes.split(",")}:
        raise RuntimeError(f"GHCR publish refused: token lacks write:packages (granted: {scopes or 'none'}). " + FIX)
    login_kind = "registry" if "apptainer" in Path(args.runtime).name else "remote"
    subprocess.run([args.runtime, login_kind, "login", "--username", args.username,
                    "--password-stdin", "oras://ghcr.io"], input=token + "\n", text=True, check=True)
    source_sha = sha256(args.sif)
    print(f"Input SIF {source_sha}", flush=True)
    records = []
    # Only files created by this invocation live in the temporary directory.
    with tempfile.TemporaryDirectory(prefix="fungen-ghcr-verify-") as directory:
        for tag in tags:
            uri = f"oras://ghcr.io/{args.repository}:{tag}"
            print(f"Push {uri}", flush=True)
            subprocess.run([args.runtime, "push", str(args.sif.resolve()), uri], check=True)
            record = verify(args.repository, tag, args.username, token, source_sha)
            pulled = Path(directory) / (tag + ".sif")
            subprocess.run([args.runtime, "pull", "--disable-cache", str(pulled), uri], check=True)
            actual = sha256(pulled)
            if actual != source_sha:
                raise RuntimeError(f"Round-trip sha256 mismatch for {tag}: {actual} != {source_sha}")
            record["round_trip_sha256"] = actual
            records.append(record)
            pulled.unlink()
            print(json.dumps(record, sort_keys=True), flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"repository": args.repository, "sif_sha256": source_sha,
                                      "tags": records}, indent=2) + "\n")
    print(f"Verified publication: {args.output}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        print(f"Publish command failed (exit {error.returncode}). " + FIX, file=sys.stderr)
        sys.exit(1)
    except (RuntimeError, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
