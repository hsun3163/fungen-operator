"""Deployment-owned fixed actions and workflow evidence, loaded from an explicit file."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import importlib.util
from pathlib import Path
import re
import sys
from typing import Callable

from pydantic import BaseModel


@dataclass(frozen=True)
class ActionSpec:
    name: str
    model: type[BaseModel]
    renderers: dict[str, Callable[[dict], str]]
    current_version: str = "1"
    validate: Callable | None = None
    config_text: Callable | None = None
    bindings: Callable | None = None
    validate_bindings: Callable | None = None
    reconcile: Callable | None = None
    output_fields: tuple[str, ...] = ()
    controller: bool = False
    refusal: dict | None = None
    order: float = 2.5
    description: str = ""


@dataclass(frozen=True)
class Provider:
    actions: tuple[ActionSpec, ...] = ()
    task_layout: Callable | None = None
    source_paths: tuple[str, ...] = ()


class Registry:
    def __init__(self, specs, *, task_layout=None, source_paths=()):
        self.specs = {}
        for spec in specs:
            if not re.fullmatch(r"[a-z][a-z0-9_]*", spec.name) or spec.name in self.specs or spec.name == "inspect_run":
                raise ValueError(f"duplicate or invalid action name: {spec.name}")
            if (spec.refusal is None and spec.current_version not in spec.renderers) or not all(
                    isinstance(version, str) and callable(renderer)
                    for version, renderer in spec.renderers.items()):
                raise ValueError(f"unknown current template version for {spec.name}")
            if not isinstance(spec.model, type) or not issubclass(spec.model, BaseModel):
                raise ValueError("provider action requires a strict request model")
            config = spec.model.model_config
            if config.get("extra") != "forbid" or not config.get("strict"):
                raise ValueError("provider request models must be strict and forbid extra fields")
            self.specs[spec.name] = spec
        self.models = {name: spec.model for name, spec in self.specs.items()}
        self.task_layout = task_layout
        self.source_paths = tuple(dict.fromkeys(str(Path(path).resolve()) for path in source_paths))

    def spec(self, name):
        try:
            return self.specs[name]
        except KeyError as exc:
            raise ValueError(f"unknown action: {name}") from exc

    def version(self, name):
        return self.spec(name).current_version

    def render(self, name, slots, version=None):
        spec = self.spec(name)
        version = spec.current_version if version is None else version
        if version not in spec.renderers:
            raise ValueError(f"unknown template version for {name}: {version}")
        if set(slots) != {"arguments", "bindings"}:
            raise ValueError("invalid slot envelope")
        spec.model.model_validate(slots["arguments"])
        return spec.renderers[version](slots)

    def order(self, name):
        return self.spec(name).order


def builtin_registry():
    from .actions import MODELS, render
    return Registry(ActionSpec(name, model, {"1": lambda slots, name=name: render(name, slots)},
                               controller=name == "initiate_run")
                    for name, model in MODELS.items())


def load_registry(deployment, deployment_file=None):
    base = builtin_registry()
    if not deployment.action_provider:
        return base
    file_name, separator, factory_name = deployment.action_provider.partition(":")
    if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", factory_name):
        raise ValueError("action_provider must name a Python file and factory")
    path = Path(file_name)
    if not path.is_absolute():
        if deployment_file is None:
            raise ValueError("relative action_provider requires a deployment file")
        path = Path(deployment_file).resolve().parent / path
    path = path.resolve()
    raw = path.read_bytes()
    module_name = "_fungen_provider_" + hashlib.sha256(str(path).encode() + raw).hexdigest()
    module_spec = importlib.util.spec_from_file_location(module_name, path)
    if module_spec is None or module_spec.loader is None:
        raise ValueError("cannot load deployment action provider")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_name] = module
    try:
        # Each registry reloads its provider and declared sibling modules. The
        # identity catalog and renderer therefore observe the same source edit.
        exec(compile(raw, str(path), "exec", dont_inherit=True), module.__dict__)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    provider = getattr(module, factory_name)(deployment)
    if not isinstance(provider, Provider):
        raise ValueError("action provider factory must return Provider")
    sources = [str(path)]
    for name in provider.source_paths:
        source = Path(name)
        sources.append(str(source if source.is_absolute() else path.parent / source))
    if not all(Path(source).is_file() for source in sources):
        raise ValueError("provider source_paths must name existing files")
    return Registry([*base.specs.values(), *provider.actions], task_layout=provider.task_layout,
                    source_paths=sources)
