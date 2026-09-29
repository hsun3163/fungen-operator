"""Deterministic manuscript masking. Run through `librarian mask`; no model decisions."""
from __future__ import annotations

import argparse
import copy
import difflib
import fcntl
import hashlib
import html
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
import tomllib

import zstandard
from markdown_it import MarkdownIt
from markdown_it.rules_inline.emphasis import tokenize as emphasis

# The adapter imports this module too when the thin CLI is run as a script.
if __name__ == '__main__':
    sys.modules['masking'] = sys.modules[__name__]

ID = re.compile(r"\{\{([A-Z][A-Z0-9]*-[A-Z2-7]{4})\}\}")
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
TRANSLATE = str.maketrans({**{c: "-" for c in "‐‑‒–—―−﹘﹣－"},
                           **{c: " " for c in "\u00a0\u2007\u2009\u200a\u202f"}, "×": "x"})
TOKEN = re.compile(r"[^\W_]+(?:[.-][^\W_]+)*", re.UNICODE)
NUMBER = re.compile(r"[+-]?(?:\d[\d,]*\.?\d*|\.\d+)(?:[Ee][+-]?\d+|\s*x\s*10\s*[+-]?\d+)?%?")
STYLES = ("bold", "italic", "superscript", "subscript", "code", "link")


class MaskError(Exception):
    """Only fixed error codes, valid IDs and numeric positions reach the terminal."""
    def __init__(self, code, position=0, identifier=None):
        message = f"{code} at position {position}"
        if identifier and ID.fullmatch(identifier):
            message += f" ({identifier})"
        super().__init__(message)


def normalize(text):
    return text.translate(TRANSLATE)


def fingerprint(data):
    return hashlib.sha256(data).hexdigest()


def chars(runs):
    return [(c, {k: run[k] for k in STYLES if run.get(k)})
            for run in runs for c in run["text"]]


def runs_from_chars(items):
    result = []
    for c, style in items:
        if result and {k: v for k, v in result[-1].items() if k != "text"} == style:
            result[-1]["text"] += c
        else:
            result.append({"text": c, **style})
    return result


def plain(runs):
    return "".join(r["text"] for r in runs)


def validate_runs(value, runs):
    if not isinstance(value, str) or not value.strip() or not isinstance(runs, list):
        raise MaskError("invalid-value")
    for run in runs:
        if not isinstance(run, dict) or set(run) - {"text", *STYLES} or not isinstance(run.get("text"), str):
            raise MaskError("invalid-runs")
        if any(k != "link" and k != "text" and type(v) is not bool for k, v in run.items()):
            raise MaskError("invalid-runs")
        if run.get("link") and not isinstance(run["link"], str):
            raise MaskError("invalid-runs")
        if run.get("superscript") and run.get("subscript"):
            raise MaskError("invalid-runs")
    if plain(runs) != value:
        raise MaskError("invalid-runs")


def parse_inline(tokens, position):
    active = {"bold": 0, "italic": 0, "superscript": 0, "subscript": 0}
    link = None
    out = []
    for token in tokens:
        kind = token.type
        if kind in ("strong_open", "strong_close", "em_open", "em_close"):
            key = "bold" if kind.startswith("strong") else "italic"
            active[key] += 1 if kind.endswith("open") else -1
            continue
        if kind == "link_open":
            link = token.attrGet("href")
            continue
        if kind == "link_close":
            link = None
            continue
        if kind == "html_inline":
            match = re.fullmatch(r"<(\/)?(sup|sub)>", token.content, re.I)
            if match:
                key = "superscript" if match[2].lower() == "sup" else "subscript"
                active[key] += -1 if match[1] else 1
                if active[key] < 0:
                    raise MaskError("formatting", position)
                continue
            if not token.content.startswith("<!--"):
                raise MaskError("unsupported-markup", position)
        if kind not in ("text", "code_inline", "softbreak", "hardbreak", "html_inline"):
            raise MaskError("unsupported-markup", position)
        style = {k: True for k, count in active.items() if count}
        if link:
            style["link"] = link
        if kind == "code_inline":
            style["code"] = True
        text = "\n" if kind in ("softbreak", "hardbreak") else token.content
        out.extend((c, style.copy()) for c in text)
    if any(active.values()) or link:
        raise MaskError("formatting", position)
    return runs_from_chars(out)


def markdown_blocks(text):
    """Use CommonMark for structure; retain untouched source blocks verbatim."""
    parser = MarkdownIt("commonmark")
    groups = {}

    def located(state, silent):
        first, start = len(state.delimiters), state.pos
        accepted = emphasis(state, silent)
        if accepted and not silent:
            group = [state.tokens[d.token] for d in state.delimiters[first:]]
            if len(group) >= 2:
                groups.setdefault(id(state), []).append((start, group))
        return accepted

    def checked(state):
        for start, group in groups.pop(id(state), []):
            if any(t.type == "text" and t.content for t in group):
                raise MaskError("bold-markers", start)

    parser.inline.ruler.at("emphasis", located)
    parser.inline.ruler2.after("emphasis", "masking_check", checked)
    parsed = parser.parse(text)
    for token in parsed:
        if token.type == "html_block" and not token.content.lstrip().startswith("<!--"):
            raise MaskError("unsupported-markup", token.map[0] if token.map else 0)
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    result, cursor = [], 0
    for i, token in enumerate(parsed):
        if token.type != "inline":
            continue
        start, stop = token.map
        a, b = offsets[start], offsets[stop]
        if a < cursor:
            raise MaskError("overlapping-blocks", a)
        if a > cursor:
            result.append({"raw": text[cursor:a], "literal": True, "runs": [{"text": text[cursor:a]}], "position": cursor})
        raw = text[a:b]
        pieces = token.content.split("\n")
        prefixes = []
        for j, piece in enumerate(pieces):
            line = lines[start + j].rstrip("\r\n")
            index = line.find(piece)
            if index < 0:
                raise MaskError("source-map", a)
            prefixes.append(line[:index])
        last_line = lines[start + len(pieces) - 1]
        suffix = last_line[len(prefixes[-1]) + len(pieces[-1]):]
        suffix += "".join(lines[start + len(pieces):stop])
        heading = int(parsed[i - 1].tag[1:]) if i and parsed[i - 1].type == "heading_open" else 0
        result.append({"raw": raw, "literal": False, "runs": parse_inline(token.children or [], a),
                       "prefixes": prefixes, "suffix": suffix, "heading": heading, "position": a})
        cursor = b
    if cursor < len(text):
        result.append({"raw": text[cursor:], "literal": True, "runs": [{"text": text[cursor:]}], "position": cursor})
    return result


def escape_md(text):
    # Placeholders deliberately contain no Markdown-sensitive underscores/brackets.
    return re.sub(r"([\\`*_[\]<>])", r"\\\1", text)


def render_runs(runs):
    """Canonical Markdown; keep adjacent bold runs inside a single bold wrapper."""
    items = [(c, style.copy()) for c, style in chars(runs)]
    # CommonMark delimiters cannot open/close against whitespace. Keep that
    # whitespace outside emphasis without changing the visible text.
    for key in ("bold", "italic"):
        for direction in (range(len(items)), range(len(items) - 1, -1, -1)):
            boundary = True
            for i in direction:
                c, style = items[i]
                if not style.get(key):
                    boundary = True
                elif boundary and c.isspace():
                    style.pop(key)
                else:
                    boundary = False
    runs = runs_from_chars(items)
    result, active = [], []
    for run in runs:
        styles = [s for s in ("bold", "italic", "superscript", "subscript") if run.get(s)]
        common = 0
        while common < min(len(styles), len(active)) and styles[common] == active[common]:
            common += 1
        close = {"bold": "**", "italic": "*", "superscript": "</sup>", "subscript": "</sub>"}
        opening = {"bold": "**", "italic": "*", "superscript": "<sup>", "subscript": "<sub>"}
        result.extend(close[s] for s in reversed(active[common:]))
        result.extend(opening[s] for s in styles[common:])
        active = styles
        value = escape_md(run["text"])
        if run.get("code"):
            delimiter = "`" * (max([len(m[0]) for m in re.finditer(r"`+", run["text"])] or [0]) + 1)
            value = delimiter + " " + run["text"] + " " + delimiter
        if run.get("link"):
            if any(c in run["link"] for c in "\n\r"):
                raise MaskError("invalid-link")
            value = "[" + value + "](<" + run["link"].replace(">", "%3E") + ">)"
        result.append(value)
    result.extend({"bold": "**", "italic": "*", "superscript": "</sup>", "subscript": "</sub>"}[s]
                  for s in reversed(active))
    return "".join(result)


def render_block(block, runs):
    if runs == block["runs"]:
        return block["raw"]
    if block.get("literal"):
        return plain(runs)
    lines = render_runs(runs).split("\n")
    prefixes = block["prefixes"]
    return "\n".join(prefixes[min(i, len(prefixes) - 1)] + line for i, line in enumerate(lines)) + block["suffix"]


def protected_ranges(items, heading=False):
    if heading:
        return []
    text = "".join(c for c, _ in items)
    ranges, start = [], None
    for i, (_, style) in enumerate(items + [("", {})]):
        if style.get("bold") and start is None:
            start = i
        elif not style.get("bold") and start is not None:
            ranges.append((start, i))
            start = None
    merged = []
    for a, b in ranges:
        if merged and not text[merged[-1][1]:a].strip():
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    tokens = list(TOKEN.finditer(normalize(text)))
    expanded = []
    for a, b in merged:
        while a < b and text[a].isspace():
            a += 1
        while b > a and text[b - 1].isspace():
            b -= 1
        if a == b:
            continue
        for token in tokens:
            if token.start() < a < token.end():
                a = token.start()
            if token.start() < b < token.end():
                b = token.end()
        if expanded and a <= expanded[-1][1]:
            expanded[-1] = (expanded[-1][0], max(b, expanded[-1][1]))
        else:
            expanded.append((a, b))
    return expanded


def sentence(text, a, b):
    start, end = 0, len(text)
    for m in re.finditer(r"[.!?](?:\s+|$)", text):
        if m.end() <= a:
            start = m.end()
        elif m.start() >= b:
            end = m.end()
            break
    return text[start:end].strip()


def fresh_id(dictionary, kind):
    used = {key[-6:-2] for key in dictionary["entries"]}
    for _ in range(128):
        suffix = "".join(secrets.choice(ALPHABET) for _ in range(4))
        if suffix not in used:
            return "{{" + kind + "-" + suffix + "}}"
    raise MaskError("id-capacity")


def add_entry(dictionary, document, value=None, runs=None, description=None, context="", kind=None):
    basis = value if value is not None else description
    kind = kind or ("VALUE" if NUMBER.fullmatch(normalize(basis).strip()) else "TEXT")
    if not re.fullmatch(r"[A-Z][A-Z0-9]*", kind):
        raise MaskError("invalid-type")
    identifier = fresh_id(dictionary, kind)
    entry = {"id": identifier, "value": value, "runs": runs or [], "type": kind,
             "context": context, "documents": [document]}
    if value is None:
        entry.update(description=description, status="pending")
    dictionary["entries"][identifier] = entry
    return identifier


def doc_entries(dictionary, document):
    return [e for e in dictionary["entries"].values() if document in e["documents"]]


def value_id(dictionary, document, value, runs, context, pending=True):
    normalized = normalize(value)
    entries = doc_entries(dictionary, document)
    if pending:
        matches = [e for e in entries if e["value"] is None and normalize(e["description"]) == normalized]
        if matches:
            return matches[0]["id"]
    matches = [e for e in entries if e["value"] is not None and normalize(e["value"]) == normalized]
    if len(matches) == 1:
        return matches[0]["id"]
    if len(matches) > 1:
        generics = dictionary["documents"][document].setdefault("generics", {})
        if normalized not in generics:
            generics[normalized] = add_entry(dictionary, document, value, runs, context=context)
        return generics[normalized]
    return add_entry(dictionary, document, value, runs, context=context)


def mask_runs(dictionary, document, runs, heading=False, literal=False):
    items = chars(runs)
    text = plain(runs)
    replacements = []
    for a, b in protected_ranges(items, heading or literal):
        if ID.fullmatch(text[a:b]):
            strict_placeholders(text[a:b], dictionary, document)
            replacements.append((a, b, text[a:b]))
            continue
        captured = runs_from_chars([(c, {k:v for k,v in s.items() if k != "bold"}) for c, s in items[a:b]])
        identifier = value_id(dictionary, document, text[a:b], captured, sentence(text, a, b))
        replacements.append((a, b, identifier))
    normalized = normalize(text)
    candidates = {normalize(e["value"]): e for e in doc_entries(dictionary, document) if e["value"] is not None}
    tokens = [(m.start(), m.end()) for m in TOKEN.finditer(normalized)]
    for value in sorted(candidates, key=lambda v: (-len(v), v)):
        if not value:
            continue
        for match in re.finditer(re.escape(value), normalized):
            a, b = match.span()
            if any(a < y and b > x for x, y, _ in replacements):
                continue
            if any(x < a < y or x < b < y for x, y in tokens):
                continue
            entry = candidates[value]
            identifier = value_id(dictionary, document, entry["value"], entry["runs"], sentence(text, a, b), pending=False)
            replacements.append((a, b, identifier))
    for a, b, identifier in sorted(replacements, reverse=True):
        items[a:b] = [(c, {}) for c in identifier]
    return runs_from_chars(items)


def strict_placeholders(text, dictionary, document):
    decoded = html.unescape(re.sub(r"\\([{}\[\]])", r"\1", text))
    if decoded != text and ID.findall(decoded) != ID.findall(text):
        raise MaskError("escaped-placeholder", next((i for i,c in enumerate(text) if c in "\\&"), 0))
    matches = list(ID.finditer(text))
    rest = list(text)
    for match in matches:
        if match.start() and text[match.start() - 1] == "\\":
            raise MaskError("escaped-placeholder", match.start())
        entry = dictionary["entries"].get(match[0])
        if not entry or document not in entry["documents"]:
            raise MaskError("unknown-placeholder", match.start(), match[0])
        rest[match.start():match.end()] = " " * len(match[0])
    residual = "".join(rest)
    malformed = re.search(r"\{\{|\}\}|\{[A-Za-z]+[-_]|\[{1,2}[A-Z]+[-_]", residual)
    if not malformed and decoded != text:
        malformed = re.search(r"\{\{|\}\}", ID.sub("", decoded))
    if malformed:
        raise MaskError("malformed-placeholder", malformed.start())
    return matches


def unmask_runs(dictionary, document, runs, heading=False, literal=False):
    text = plain(runs)
    strict_placeholders(text, dictionary, document)
    items = chars(runs)
    requests = []
    for a, b in protected_ranges(items, heading or literal):
        value = text[a:b]
        if ID.fullmatch(value):
            continue
        identifier = add_entry(dictionary, document, description=value, context=sentence(text, a, b))
        requests.append((a, b, identifier))
    for a, b, identifier in reversed(requests):
        items[a:b] = [(c, {}) for c in identifier]
    rewritten = plain(runs_from_chars(items))
    matches = strict_placeholders(rewritten, dictionary, document)
    masked_items = copy.deepcopy(items)
    for match in reversed(matches):
        entry = dictionary["entries"][match[0]]
        replacement = entry["runs"] if entry["value"] is not None else [{"text": entry["description"]}]
        resolved = [(c, {**style, "bold": True}) for c, style in chars(replacement)]
        items[match.start():match.end()] = resolved
        masked_items[match.start():match.end()] = [(c, {}) for c in match[0]]
    return runs_from_chars(items), runs_from_chars(masked_items)


def empty_dictionary():
    return {"version": 1, "entries": {}, "documents": {}}


def load_dictionary(path):
    if not path.exists():
        return empty_dictionary()
    try:
        dictionary = json.loads(zstandard.ZstdDecompressor().decompress(path.read_bytes()))
        if dictionary["version"] != 1 or not isinstance(dictionary["entries"], dict) or not isinstance(dictionary["documents"], dict):
            raise ValueError()
        for key, entry in dictionary["entries"].items():
            if not ID.fullmatch(key) or entry["id"] != key or entry["type"] != ID.fullmatch(key)[1].rsplit("-", 1)[0]:
                raise ValueError()
            if not isinstance(entry["documents"], list) or not isinstance(entry["context"], str):
                raise ValueError()
            if entry["value"] is None:
                if entry["status"] not in ("pending", "needs-human") or not isinstance(entry["description"], str):
                    raise ValueError()
            else:
                validate_runs(entry["value"], entry["runs"])
                if "status" in entry or "description" in entry:
                    raise ValueError()
        return dictionary
    except Exception:
        raise MaskError("dictionary-read") from None


def stage_file(path, data):
    fd, name = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        return Path(name)
    except BaseException:
        Path(name).unlink(missing_ok=True)
        raise


def atomic_write(path, data):
    temporary = stage_file(path, data)
    try:
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def save_dictionary(path, dictionary):
    previous = load_dictionary(path)
    for key, entry in previous["entries"].items():
        current = dictionary["entries"].get(key)
        if current is None or not set(entry["documents"]).issubset(current["documents"]):
            raise MaskError("immutable-entry", identifier=key)
        if entry["value"] is not None and any(current[k] != entry[k] for k in ("value", "runs", "type")):
            raise MaskError("immutable-entry", identifier=key)
    try:
        encoded = json.dumps(dictionary, ensure_ascii=False, indent=2).encode()
        atomic_write(path, zstandard.ZstdCompressor().compress(encoded))
    except Exception:
        raise MaskError("dictionary-save") from None


def statuses(dictionary, masked):
    identifiers = dict.fromkeys(m[0] for m in ID.finditer(masked))
    return "".join(key + "\t" + dictionary["entries"][key].get("status", "resolved") + "\n" for key in identifiers)


def publish(dictionary_path, dictionary, masked, masked_path, status_path):
    staged = []
    try:
        for path, text in ((status_path, statuses(dictionary, masked)), (masked_path, masked)):
            staged.append((stage_file(path, text.encode()), path))
        save_dictionary(dictionary_path, dictionary)
        for temporary, path in staged:
            os.replace(temporary, path)
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)


def check_masked(dictionary, document, masked):
    strict_placeholders(masked, dictionary, document)
    public = normalize(ID.sub(lambda match: " " * len(match[0]), masked))
    tokens = [(match.start(), match.end()) for match in TOKEN.finditer(public)]
    for entry in doc_entries(dictionary, document):
        if entry["value"] is None:
            continue
        for match in re.finditer(re.escape(normalize(entry["value"])), public):
            a, b = match.span()
            if not any(x < a < y or x < b < y for x, y in tokens):
                # Covers a private value in Markdown link targets or structural
                # syntax that cannot safely be replaced as visible prose.
                raise MaskError("unmasked-structural-value", a, entry["id"])


def export_markdown(dictionary, document, text):
    blocks = markdown_blocks(text)
    # Register every body span first, so known values in earlier headings are covered.
    for block in blocks:
        if not block.get("literal"):
            mask_runs(dictionary, document, block["runs"], bool(block.get("heading")))
    return "".join(render_block(b, mask_runs(dictionary, document, b["runs"], bool(b.get("heading")), b.get("literal", False))) for b in blocks)


def import_markdown(dictionary, document, text):
    strict_placeholders(text, dictionary, document)
    human, masked = [], []
    for block in markdown_blocks(text):
        a, b = unmask_runs(dictionary, document, block["runs"], bool(block.get("heading")), block.get("literal", False))
        human.append(render_block(block, a))
        masked.append(render_block(block, b))
    return "".join(human), "".join(masked)


def preserve_paragraphs(live, desired):
    old, new = markdown_blocks(live), markdown_blocks(desired)
    def signature(block):
        return json.dumps([block.get("heading", 0), block.get("literal", False), block["runs"]], sort_keys=True)
    matcher = difflib.SequenceMatcher(a=[signature(b) for b in old], b=[signature(b) for b in new], autojunk=False)
    replacements = {}
    for tag, a, b, c, d in matcher.get_opcodes():
        if tag == "equal":
            for oi, ni in zip(range(a, b), range(c, d)):
                replacements[ni] = old[oi]["raw"]
    return "".join(replacements.get(i, block["raw"]) for i, block in enumerate(new))


def settings(config_path):
    try:
        config_path = config_path.expanduser().resolve()
        codex_home = config_path.parent
        if codex_home == (Path.home() / ".codex").resolve():
            raise MaskError("shared-codex-home")
        config = tomllib.loads(config_path.read_text())["masking"]
        dictionary = (codex_home / Path(config["dictionary"]).expanduser()).resolve()
        if dictionary.name != "dict.json.zst" or dictionary.parent != codex_home.parent:
            raise MaskError("dictionary-location")
        if any((parent / ".git").is_file() or (parent / ".git/HEAD").is_file() for parent in dictionary.parents):
            raise MaskError("dictionary-in-repository")
        return {**config, "dictionary_path": dictionary}
    except MaskError:
        raise
    except Exception:
        raise MaskError("configuration") from None


def read_source(source, config):
    if source["kind"] == "markdown":
        data = Path(source["path"]).read_bytes()
        return data.decode("utf-8"), fingerprint(data)
    from google_docs import read_document
    return read_document(source, config)


def check_revision(record, revision):
    if revision != record["revision"]:
        raise MaskError("source-revision-changed")


def write_source(source, live, human, revision, config):
    if source["kind"] == "markdown":
        path = Path(source["path"])
        if fingerprint(path.read_bytes()) != revision:
            raise MaskError("source-revision-changed")
        updated = preserve_paragraphs(live, human)
        if updated != live:
            atomic_write(path, updated.encode())
        return fingerprint(updated.encode())
    from google_docs import write_document
    return write_document(source, live, human, revision, config)


def do_export(config, document, source, masked_path, status_path):
    dictionary = load_dictionary(config["dictionary_path"])
    existing = dictionary["documents"].get(document)
    if existing and existing["source"] != source:
        raise MaskError("document-source-changed")
    if source["kind"] == "markdown" and Path(source["path"]) in (masked_path, status_path):
        raise MaskError("output-is-source")
    if masked_path == status_path or config["dictionary_path"] in (masked_path, status_path):
        raise MaskError("output-location")
    live, revision = read_source(source, config)
    record = dictionary["documents"].setdefault(document, {})
    record.update(source=source, revision=revision, masked=str(masked_path), slots=str(status_path))
    if source["kind"] == "markdown":
        masked = export_markdown(dictionary, document, live)
    else:
        from google_docs import export_document
        masked = export_document(dictionary, document, live, source)
    check_masked(dictionary, document, masked)
    # Recheck before releasing a snapshot. Google revision guards also protect import.
    _, current = read_source(source, config)
    if current != revision:
        raise MaskError("source-revision-changed")
    publish(config["dictionary_path"], dictionary, masked, masked_path, status_path)


def do_import(config, document):
    dictionary = load_dictionary(config["dictionary_path"])
    record = dictionary["documents"].get(document)
    if record is None:
        raise MaskError("unknown-document")
    masked_path, status_path = Path(record["masked"]), Path(record["slots"])
    source = record["source"]
    live, revision = read_source(source, config)
    check_revision(record, revision)
    incoming = masked_path.read_text()
    human, masked = import_markdown(dictionary, document, incoming)
    check_masked(dictionary, document, masked)
    save_dictionary(config["dictionary_path"], dictionary)
    new_revision = write_source(source, live, human, revision, config)
    record["revision"] = new_revision
    publish(config["dictionary_path"], dictionary, masked, masked_path, status_path)


def do_upload(config, document, markdown_path, masked_path, status_path, folder, title):
    """Initialize a Google human source from Markdown, without replacing existing Docs."""
    from google_docs import (ensure_folder, ensure_file, read_document, write_document,
                             desired_paragraphs, paragraphs, signature)
    dictionary = load_dictionary(config["dictionary_path"])
    record = dictionary['documents'].setdefault(document, {})
    if record.get('upload_complete'):
        return {'folder': record['drive_folder'], 'document': record['source']['id']}
    if record.get('source') and not record.get('upload_seed'):
        raise MaskError('document-already-registered')
    if masked_path == status_path or config['dictionary_path'] in (markdown_path, masked_path, status_path):
        raise MaskError('output-location')
    data = markdown_path.read_bytes()
    seed = {'path': str(markdown_path), 'hash': fingerprint(data), 'folder': folder, 'title': title,
            'masked': str(masked_path), 'slots': str(status_path)}
    if record.get('upload_seed', seed) != seed:
        raise MaskError('upload-source-changed')
    record['upload_seed'] = seed
    text = data.decode('utf-8')
    # The previous manuscript integration used named NUM/INFO tokens. Their
    # names specify pending requests, never retrieved or inferred values.
    legacy = re.compile(r'\{\{(NUM|INFO):([A-Za-z0-9_]+)\}\}')
    mapping = record.setdefault('legacy_slots', {})
    def migrate(match):
        token = match[0]
        if token not in mapping:
            mapping[token] = add_entry(dictionary, document, description=match[2].replace('_', ' '),
                                      context=sentence(text, match.start(), match.end()),
                                      kind='VALUE' if match[1] == 'NUM' else 'TEXT')
        return mapping[token]
    migrated = legacy.sub(migrate, text)
    strict_placeholders(migrated, dictionary, document)
    masked = export_markdown(dictionary, document, migrated)
    check_masked(dictionary, document, masked)
    human, masked = import_markdown(dictionary, document, masked)
    desired = desired_paragraphs(human)  # Validate before any remote mutation.
    save_dictionary(config['dictionary_path'], dictionary)
    parent = ensure_folder(config, folder)
    identifier = ensure_file(config, parent, title, 'application/vnd.google-apps.document', {
        'librarianDocument': fingerprint((str(masked_path) + '\n' + document).encode()),
        'librarianSeed': seed['hash']})
    source = {'kind': 'google', 'id': identifier, 'tab': None}
    live, revision = read_document(source, config)
    current = paragraphs(live, source)
    if current and [signature(b) for b in current] != [signature(b) for b in desired]:
        raise MaskError('existing-google-content')
    if fingerprint(markdown_path.read_bytes()) != seed['hash']:
        raise MaskError('upload-source-changed')
    if not current:
        revision = write_document(source, live, human, revision, config)
    verified, verified_revision = read_document(source, config)
    if verified_revision != revision or [signature(b) for b in paragraphs(verified, source)] != [signature(b) for b in desired]:
        raise MaskError('google-upload-verification')
    record.update(source=source, revision=revision, masked=str(masked_path), slots=str(status_path),
                  drive_folder=parent)
    publish(config['dictionary_path'], dictionary, masked, masked_path, status_path)
    record['upload_complete'] = True
    save_dictionary(config['dictionary_path'], dictionary)
    return {'folder': parent, 'document': identifier}


def request_slots(slots):
    prompt = ("Retrieve or compute only the requested private values. Do not classify, disambiguate, choose IDs, "
              "or edit files. Return exactly one JSON object keyed by the supplied IDs. Each result is "
              "{\"value\":\"plain text\",\"runs\":[{\"text\":\"plain text\"}]} or {\"status\":\"needs-human\"}. "
              "Runs may mark italic, superscript and subscript with true. Use needs-human if unresolved. "
              "The response stays inside the local masking process. Requests:\n" + json.dumps(slots, ensure_ascii=False))
    try:
        result = subprocess.run([str(Path(__file__).with_name("librarian")), "--slots"],
                                input=prompt, text=True, capture_output=True, check=True)
        return json.loads(result.stdout)
    except Exception:
        return {}


def bind_slots(dictionary, document, replies):
    pending = [e for e in doc_entries(dictionary, document) if e.get("status") == "pending"]
    if not isinstance(replies, dict) or set(replies) - {e["id"] for e in pending}:
        raise MaskError("retrieval-response")
    for entry in pending:
        result = replies.get(entry["id"], {})
        if not isinstance(result, dict) or result.get("status") == "needs-human" or "value" not in result:
            entry["status"] = "needs-human"
            continue
        value = result["value"]
        runs = result.get("runs", [{"text": value}])
        try:
            validate_runs(value, runs)
            if "{{" in value or "}}" in value:
                raise MaskError("invalid-value")
        except MaskError:
            entry["status"] = "needs-human"
            continue
        entry.update(value=value, runs=[{k:v for k,v in r.items() if k != "bold"} for r in runs])
        entry.pop("status")
        entry.pop("description")


def do_retrieve(config, document, requester=request_slots):
    dictionary = load_dictionary(config["dictionary_path"])
    record = dictionary["documents"].get(document)
    if record is None:
        raise MaskError("unknown-document")
    live, revision = read_source(record["source"], config)
    check_revision(record, revision)
    masked_path, status_path = Path(record["masked"]), Path(record["slots"])
    incoming = masked_path.read_text()
    strict_placeholders(incoming, dictionary, document)
    for block in markdown_blocks(incoming):
        if not block.get("literal"):
            text = plain(block["runs"])
            if any(not ID.fullmatch(text[a:b]) for a, b in protected_ranges(chars(block["runs"]), bool(block.get("heading")))):
                raise MaskError("import-slot-requests-first", block["position"])
    slots = [{k: e[k] for k in ("id", "description", "context")} for e in doc_entries(dictionary, document)
             if e.get("status") == "pending"]
    if not slots:
        return
    replies = requester(slots)
    # Long-running retrieval must never overwrite intervening human edits.
    live, current = read_source(record["source"], config)
    check_revision(record, current)
    if masked_path.read_text() != incoming:
        raise MaskError("masked-file-changed")
    # Only slots requested in this round can be bound.
    if not isinstance(replies, dict) or set(replies) - {s["id"] for s in slots}:
        raise MaskError("retrieval-response")
    bind_slots(dictionary, document, replies)
    human, masked = import_markdown(dictionary, document, incoming)
    check_masked(dictionary, document, masked)
    save_dictionary(config["dictionary_path"], dictionary)
    record["revision"] = write_source(record["source"], live, human, current, config)
    publish(config["dictionary_path"], dictionary, masked, masked_path, status_path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export")
    export.add_argument("--document", required=True)
    sources = export.add_mutually_exclusive_group(required=True)
    sources.add_argument("--markdown", type=Path)
    sources.add_argument("--google-doc")
    export.add_argument("--tab")
    export.add_argument("--masked", type=Path, required=True)
    export.add_argument("--slots", type=Path)
    upload = sub.add_parser('upload', help='Create the initial Google Doc from Markdown')
    upload.add_argument('--document', required=True)
    upload.add_argument('--markdown', type=Path, required=True)
    upload.add_argument('--masked', type=Path, required=True)
    upload.add_argument('--slots', type=Path)
    upload.add_argument('--folder', required=True)
    upload.add_argument('--title', required=True)
    for name in ("import", "retrieve"):
        sub.add_parser(name).add_argument("--document", required=True)
    sub.add_parser("sync-dictionary")
    args = parser.parse_args(argv)
    try:
        config = settings(args.config)
        # Lock the containing directory, whose inode survives atomic replacement;
        # the dictionary remains the only persistent file for this mechanism.
        lock = os.open(config["dictionary_path"].parent, os.O_RDONLY | os.O_DIRECTORY)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.command == 'upload':
            masked = args.masked.expanduser().resolve()
            slots = args.slots.expanduser().resolve() if args.slots else masked.with_suffix('.slots.tsv')
            result = do_upload(config, args.document, args.markdown.expanduser().resolve(), masked, slots,
                               args.folder, args.title)
            print(json.dumps({'folder': 'https://drive.google.com/drive/folders/' + result['folder'],
                              'document': 'https://docs.google.com/document/d/' + result['document'] + '/edit'}))
        elif args.command == "export":
            source = {"kind": "markdown", "path": str(args.markdown.expanduser().resolve())} if args.markdown else {
                "kind": "google", "id": args.google_doc, "tab": args.tab}
            masked = args.masked.expanduser().resolve()
            slots = args.slots.expanduser().resolve() if args.slots else masked.with_suffix(".slots.tsv")
            do_export(config, args.document, source, masked, slots)
        elif args.command == "import":
            do_import(config, args.document)
        elif args.command == "retrieve":
            do_retrieve(config, args.document)
        else:
            from google_docs import sync_dictionary
            sync_dictionary(load_dictionary(config["dictionary_path"]), config)
        print("OK")
        return 0
    except MaskError as error:
        print(str(error), file=sys.stderr)
        return 1
    except Exception:
        # Never render underlying exception messages, HTTP bodies or tracebacks.
        print("operation-failed at position 0", file=sys.stderr)
        return 1
    finally:
        if "lock" in locals():
            os.close(lock)


if __name__ == "__main__":
    sys.exit(main())
