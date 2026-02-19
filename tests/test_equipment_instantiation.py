"""Verify every TestEquipment subclass can be instantiated without hardware.

Catches:
  - Unimplemented abstract methods (TypeError on instantiation)
  - Crashes in __init__ body (attribute errors, bad registry lookups, etc.)
  - Import errors in driver modules (caught at collection time)

All connection handler I/O is patched out. query() returns "0" so that any
post-init calls like float(conn.query(...)) or int(conn.query(...)) succeed.
New drivers are picked up automatically via equipment_manager.get_instruments.
"""

import inspect
import pytest
from contextlib import ExitStack
from unittest.mock import patch

import EEequipment.TestEquipment as _te
from EEequipment import equipment_manager

FAKE_ADDR = "FAKE_ADDR"

# Collected at import time — also catches bad module-level code in drivers.
# Filter out the abstract base classes defined in TestEquipment.py itself;
# only concrete driver classes (defined in their own subpackage files) are tested.
_te_file = inspect.getfile(_te.TestEquipment)
ALL_CLASSES = [
    (name, cls) for name, cls in equipment_manager.get_instruments("all").items()
    if inspect.getfile(cls) != _te_file
]

HANDLER_PATCHES = [
    ("EEequipment.TestEquipment.PyVISAHandler.connect", None),
    ("EEequipment.TestEquipment.PyVISAHandler.write",   None),
    ("EEequipment.TestEquipment.PyVISAHandler.query",   "0"),
    ("EEequipment.TestEquipment.SerialHandler.connect", None),
    ("EEequipment.TestEquipment.SerialHandler.write",   None),
    ("EEequipment.TestEquipment.SerialHandler.query",   "0"),
]


@pytest.mark.parametrize("name,cls", ALL_CLASSES, ids=[n for n, _ in ALL_CLASSES])
def test_can_instantiate(name, cls):
    with ExitStack() as stack:
        for target, retval in HANDLER_PATCHES:
            stack.enter_context(patch(target, return_value=retval))
        instance = cls(FAKE_ADDR)

    assert instance is not None, f"{name} instantiation returned None"
