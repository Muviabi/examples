import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

import pandas as pd
import pyarrow as pa


class ContractBroken(AssertionError):
    """What the function was handed or gave back is not what its contract says."""


class CapabilityMissing(AttributeError):
    """The function used a ``ctx`` handle the bench does not have."""


@dataclass(frozen=True)
class Window:
    """The period a run covers: ``start`` is ``None`` on a flow's first run, ``end`` is excluded."""

    start: Optional[datetime]
    end: datetime


class Context:
    """The part of Muvia's ``ctx`` every function has."""

    def __init__(self, window: Window, preview: bool):
        self.window = window
        self.preview = preview
        self.logger = logging.getLogger("muvia.function")

    def __getattr__(self, name: str) -> Any:
        raise CapabilityMissing(
            f"ctx.{name} is not on the local bench: it needs Muvia (a capability, a sink or a file)."
        )


def load(path: str | Path) -> tuple[Callable, dict]:
    """The function's ``transform`` and its export (``key``, ``name``, ``description``, ``contract``)."""
    base = Path(path).with_suffix("")
    meta = json.loads(base.with_suffix(".json").read_text(encoding="utf-8"))
    code = base.with_suffix(".py").read_text(encoding="utf-8")
    namespace: dict[str, Any] = {"__name__": f"muvia_custom_{meta['key']}"}
    exec(compile(code, f"<{meta['key']}>", "exec"), namespace)
    transform = namespace.get("transform")
    if not callable(transform):
        raise ContractBroken("The function's code defines no transform(inputs, params, ctx).")
    return transform, meta


def run(
    path: str | Path,
    inputs: Mapping[str, Any],
    params: Optional[Mapping[str, Any]] = None,
    window: Optional[Window] = None,
    preview: bool = False,
) -> dict[str, Any]:
    """Run the function at ``path`` on ``inputs`` and return its outputs, checked."""
    transform, meta = load(path)
    contract = meta["contract"]
    params = dict(params or {})
    window = window or Window(None, datetime.now(timezone.utc).replace(tzinfo=None))

    declared = {port["name"]: port for port in contract.get("inputs", [])}
    if set(inputs) != set(declared):
        raise ContractBroken(f"Inputs {sorted(inputs)} are not the contract's {sorted(declared)}.")
    handed = {}
    for name, value in inputs.items():
        if declared[name]["type"] == "table":
            # A table reaches the function through Arrow, as in Muvia: index dropped, dtypes Arrow's.
            value = pa.Table.from_pandas(pd.DataFrame(value), preserve_index=False).to_pandas()
            _check_columns(f"input '{name}'", value, declared[name].get("columns", []), params, contract)
        handed[name] = value

    produced = transform(handed, params, Context(window, preview))

    outputs = contract.get("outputs", [])
    if not isinstance(produced, dict):
        raise ContractBroken(f"transform must return a dict of its outputs, not {type(produced).__name__}.")
    if set(produced) != {port["name"] for port in outputs}:
        raise ContractBroken(
            f"transform returned {sorted(produced)}, the contract's outputs are "
            f"{sorted(port['name'] for port in outputs)}."
        )
    for port in outputs:
        value = produced[port["name"]]
        if port["type"] == "table":
            if not isinstance(value, pd.DataFrame):
                raise ContractBroken(f"Output '{port['name']}' must be a DataFrame, not {type(value).__name__}.")
            columns = port.get("columns", []) if port.get("shape") == "fixed" else port.get("adds", [])
            _check_columns(f"output '{port['name']}'", value, columns, params, contract)
        else:
            json.dumps(value)  # what is not a table travels as JSON, as in Muvia
    return produced


def _check_columns(where: str, frame: pd.DataFrame, columns: list, params: Mapping, contract: dict) -> None:
    for column in columns:
        name = column.get("name") or _param(column["name_param"], params, contract)
        if name not in frame.columns:
            if column.get("optional"):
                continue
            raise ContractBroken(f"The {where} lacks its column '{name}'.")
        kind = column.get("kind", "any")
        if not _fits(frame[name], kind):
            raise ContractBroken(f"Column '{name}' of the {where} is {frame[name].dtype}, not {kind}.")


def _param(name: str, params: Mapping, contract: dict) -> Any:
    if name in params:
        return params[name]
    return contract.get("form_config", {}).get("properties", {}).get(name, {}).get("default")


def _fits(series: pd.Series, kind: str) -> bool:
    if kind == "any":
        return True
    if kind == "time":
        return pd.api.types.is_datetime64_any_dtype(series)
    if kind == "string":
        return pd.api.types.is_string_dtype(series) or series.dtype == object
    if kind == "boolean":
        return pd.api.types.is_bool_dtype(series)
    if pd.api.types.is_bool_dtype(series) or not pd.api.types.is_numeric_dtype(series):
        return False
    if kind == "integer" and pd.api.types.is_float_dtype(series):
        # Muvia gives an integer column with gaps as floats, and takes back whole floats as integers.
        present = series.dropna()
        return bool((present == present.round()).all())
    return kind in ("integer", "float") and (kind == "float" or pd.api.types.is_integer_dtype(series))
