"""
TODO
"""
from __future__ import annotations

import re
import typing as t
from enum import Enum
from dataclasses import dataclass
from pathlib import Path

import yaml
from tutor import hooks
from tutor.plugins.base import PLUGINS_ROOT  # to do: use of internal member

YAML_V1_ROOT = Path(PLUGINS_ROOT) / "yamlv1"
YAML_KEYS = {"name", "version", "filters"}


class LoadError(BaseException):
    """
    Something went wrong when loading/parsing a YAML-V1 plugin.
    """

    def __init__(self, path: Path, message: str):
        self.path = path
        self.message = message

    def __str__(self) -> str:
        return f"Error loading YAML V1 Plugin at '{self.path}': {self.message}"


class FilterOp(Enum):
    """
    TODO
    """

    # pylint: disable=too-few-public-methods
    add_item = "add_item"
    add_items = "add_items"
    replace = "replace"


@dataclass
class FilterCallback:
    """
    TODO
    """

    filter_name: str
    filter_op: FilterOp
    value: t.Any

    @classmethod
    def parse(cls, path, data: t.Any) -> FilterCallback:
        """
        TODO
        """
        if not (isinstance(data, dict) and {"name", "op", "value"} == set(data)):
            raise LoadError(
                path,
                "each entry in 'filters' must be a dictionary with keys 'name', 'op', and 'value'",
            )
        filter_name = data["name"]
        if not (
            isinstance(filter_name, str) and re.match(filter_name, r"^[A-Z][A-Z0-9_]*$")
        ):
            raise LoadError(path, f"invalid filter name: '{filter_name}'")
        try:
            filter_op = FilterOp(data["op"])
        except ValueError:
            raise LoadError(  # pylint: disable=raise-missing-from
                path,
                f"bad filter op {data['op']}; should be one of: "
                + ", ".join(o.value for o in FilterOp),
            )
        value = data["value"]
        if filter_op == FilterOp.add_items:
            if not isinstance(value, list):
                raise LoadError(
                    path,
                    f"when using 'op: add_items', 'value' must be a list, not a {type(value)}",
                )
        return FilterCallback(
            filter_name=filter_name, filter_op=filter_op, value=data["value"]
        )


@dataclass
class YamlV1Plugin:
    """
    TODO
    """

    name: str
    version: t.Optional[str]
    filters: list[FilterCallback]

    @classmethod
    def load(cls, path: Path) -> YamlV1Plugin:
        """
        TODO
        """
        try:
            with open(path, encoding="utf-8") as yaml_file:
                data = yaml.safe_load(yaml_file)
        except yaml.YAMLError as exc:
            raise LoadError(path, "file is not valid YAML") from exc
        except Exception as exc:
            raise LoadError(path, "file could not be opened") from exc
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
        filters = [
            FilterCallback.parse(path, filter_data) for filter_data in data["filters"]
        ]
        return YamlV1Plugin(name=name, version=version, filters=filters)


@hooks.Actions.CORE_READY.add()
def _discover_v1_yaml_plugins() -> None:
    """
    TODO
    """
    plugins = [YamlV1Plugin.load(path) for path in YAML_V1_ROOT.glob("*.yml")]
    from pprint import pprint  # pylint: disable=import-outside-toplevel

    pprint(plugins)
    raise NotImplementedError
