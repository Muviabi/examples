"""What every example must hold to be imported into Muvia's Lab and run there."""

import ast
import json
import re
import sys

import pytest

from conftest import FUNCTIONS

PAIRS = sorted(path.with_suffix("") for path in FUNCTIONS.rglob("*.json"))
KEY = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
PORT_TYPES = {"table", "text", "image", "file", "json", "scalar"}
KINDS = {"time", "string", "integer", "float", "boolean", "any"}
PARAM_TYPES = {"string", "number", "integer", "boolean"}
# What the function runtime ships (and the standard library): an import of anything else fails at run.
SHIPPED = {"numpy", "pandas", "pyarrow", "scipy", "sklearn", "statsmodels", "lightgbm", "joblib",
           "matplotlib", "openpyxl", "pywt", "onnx", "onnxruntime", "skl2onnx", "dateutil"}


def test_there_are_examples():
    assert len(PAIRS) >= 12


@pytest.mark.parametrize("base", PAIRS, ids=lambda p: p.name)
def test_each_json_has_its_code_and_names_it(base):
    meta = json.loads(base.with_suffix(".json").read_text(encoding="utf-8"))
    assert base.with_suffix(".py").is_file()
    assert meta["key"] == base.name and KEY.match(meta["key"])
    assert 1 <= len(meta["name"]) <= 120
    assert len(meta["description"]) <= 2000


@pytest.mark.parametrize("base", PAIRS, ids=lambda p: p.name)
def test_contract_holds_together(base):
    contract = json.loads(base.with_suffix(".json").read_text(encoding="utf-8"))["contract"]
    properties = contract["form_config"].get("properties", {})
    assert contract["form_config"]["type"] == "object"
    for name, schema in properties.items():
        assert schema["type"] in PARAM_TYPES, name
        assert schema.get("description"), f"parameter {name} says nothing"
    for side in ("inputs", "outputs"):
        names = [port["name"] for port in contract[side]]
        assert len(names) == len(set(names)) and all(names) and not any("#" in n for n in names)
        for port in contract[side]:
            assert port["type"] in PORT_TYPES
            for column in port.get("columns", []) + port.get("adds", []):
                assert column["kind"] in KINDS
                assert column["kind"] != "any" or side == "inputs"
                assert ("name" in column) != ("name_param" in column)
                if "name_param" in column:
                    assert column["name_param"] in properties
    table_inputs = {port["name"] for port in contract["inputs"] if port["type"] == "table"}
    for port in contract["outputs"]:
        if port.get("shape") == "fixed":
            assert port["columns"]
        if port.get("shape") == "derived":
            assert port["derived_from"] in table_inputs
    assert 1 <= contract["timeout_seconds"] <= 1800 and 0 <= contract["retries"] <= 3
    assert set(contract["targets"]) <= {"cloud", "edge"}


@pytest.mark.parametrize("base", PAIRS, ids=lambda p: p.name)
def test_code_returns_the_contracts_outputs_and_imports_what_is_shipped(base):
    contract = json.loads(base.with_suffix(".json").read_text(encoding="utf-8"))["contract"]
    tree = ast.parse(base.with_suffix(".py").read_text(encoding="utf-8"))
    transforms = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "transform"]
    assert len(transforms) == 1 and len(transforms[0].args.args) == 3

    # Muvia reads the outputs off the return statements: each a dict display with constant keys.
    outputs = {port["name"] for port in contract["outputs"]}
    returns = [node for node in ast.walk(transforms[0]) if isinstance(node, ast.Return)]
    assert returns
    for statement in returns:
        assert isinstance(statement.value, ast.Dict)
        assert {key.value for key in statement.value.keys} == outputs

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [node.module]
        else:
            continue
        for module in modules:
            top = module.split(".")[0]
            assert top in SHIPPED or top in sys.stdlib_module_names, module
