"""Sanity checks for DMM driver model name correctness.

These tests use AST parsing so they require no hardware connections.
The model name string passed to super().__init__() must match a directory
in EEequipment/ that has a config.ini — otherwise the CommandRegistry will
fail to find any commands for that driver at runtime.
"""

import ast
import pathlib

import pytest

from EEequipment.TestEquipment import get_registry

# Add new DMM drivers here as they are created
DMM_DRIVERS = [
    "EEequipment/hp3478A/hp3478A.py",
    "EEequipment/fluke8842A/fluke8842A.py",
    "EEequipment/XDM1041/xdm1041main.py",
]

ROOT = pathlib.Path(__file__).parent.parent


def extract_super_model(filepath: str) -> str | None:
    """Return the first string arg of super().__init__() in the file, or None."""
    source = (ROOT / filepath).read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "__init__"
            and isinstance(func.value, ast.Call)
            and isinstance(func.value.func, ast.Name)
            and func.value.func.id == "super"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            return node.args[0].value
    return None


@pytest.mark.parametrize("driver_path", DMM_DRIVERS)
def test_driver_model_in_registry(driver_path):
    model = extract_super_model(driver_path)
    assert model is not None, f"Could not parse model name from super().__init__() in {driver_path}"
    registry = get_registry()
    assert model in registry.commands, (
        f"{driver_path}: model name '{model}' has no matching config directory. "
        f"Expected EEequipment/{model}/config.ini to exist. "
        f"Known models: {sorted(registry.commands.keys())}"
    )
