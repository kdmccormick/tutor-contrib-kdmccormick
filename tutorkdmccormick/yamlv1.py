"""
TODO
"""
from __future__ import annoations

import re
import typing as t
import yaml
from dataclasses import dataclass
from pathlib import Path

from tutor import hooks
from tutor.plugins.base import PLUGINS_ROOT  # TODO: use of internal member

YAML_V1_ROOT = Path(PLUGINS_ROOT) / "yamlv1"
YAML_KEYS = {"name", "version", "filters"}


class LoadError(BaseException):
    def __init__(self, path: Path, message: str):
        self.path = path
        self.message = message

    def __str__(self) -> str:
        return f"Error loading YAML V1 Plugin at '{self.path}': {self.message}"


@dataclasses.dataclass
class FilterCallback:
    class Op(Enum[str]):
        add_item = "add_item"
        add_items = "add_items"
        replace = "replace"

    filtre: str
    op: Op
    value: t.Any

    @classmethod
    def parse(cls, path, data: t.Any) -> FilterCallback:
        if not (isinstance(data, dict) and {"name", "op", "value"} == set(data)):
            raise LoadError(
                path,
                f"each entry in 'filters' must be a dictionary with keys 'name', 'op', and 'value'",
            )
        name = data["name"]
        if not (isinstance(name, str) and re.match(name, r"^[A-Z][A-Z0-9_]*$")):
            raise LoadError(path, f"invalid filter name: '{filtre}'")
        try:
            op = Op(data["op"])
        except ValueError:
            raise LoadError(
                path,
                f"bad filter op {data['op']}; should be one of: "
                + ", ".join(o.value for o in Op),
            )
        value = data["value"]
        if op == Op.add_items:
            if not isinstance(value, list):
                raise LoadError(
                    path,
                    f"when using 'op: add_items', 'value' must be a list, not a {type(value)}",
                )
        return FilterCallback(filtre=name, op=op, value=data["value"])


@dataclasses.dataclass
class YamlV1Plugin:
    name: str
    version: t.Optional[str]
    filters: list[FilterCallback]

    @classmethod
    def load(cls, path: Path) -> YamlV1Plugin:
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            raise LoadError(path, "file is not valid YAML")
        except Exception as exc:
            raise LoadError(path, "file could not be opened")
        if not isinstance(data, dict):
            raise LoadError(path, "top-level data structure must be dictionary")
        if extra_keys := set(data) - {"name", "version", "filters"}:
            raise LoadError(
                path, "unrecognized top-level keys: " + ", ".join(extra_keys)
            )
        if not (name := data.get("name")):
            raise LoadError(path, "missing top-level 'name' key")
        if not isinstance(name, str):
            raise LoadError(path, f"'name' must be a string; is type {type(name)}")
        if version := data.get("version") and not isinstance(data["version"], str):
            raise LoadError(
                path,
                f"'version' must be either a string or omitted; is type {type(version)}",
            )
        if "filters" not in data:
            raise LoadError(path, "missing top-level 'filters' key")
        if not isinstance(data["filters"], list):
            raise LoadError(
                path, f"'filters' must be a list; is type {type(data['filters'])}"
            )
        filters = [FilterCallback(filter_data) for filter_data in data["filters"]]
        return YamlV1Plugin(name=name, version=version, filters=filters)


@hooks.Actions.CORE_READY.add()
def _discover_v1_yaml_plugins() -> None:
    """
    TODO
    """
    plugins = [YamlV1Plugin.load(path) for path in YAML_V1_ROOT.glob("*.yml")]
    from pprint import pprint

    pprint(plugins)
    raise NotImplementedError
