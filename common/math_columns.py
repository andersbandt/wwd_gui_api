"""
@file     math_columns.py
@author   Anders Bandt
@date     February 2026
@brief    User-defined computed columns for the data logger.

Provides a safe expression evaluator (via simpleeval) so users can define
math columns like "Power_W = PS_Vmeas1 * PS_Imeas1" that are appended to
each CSV row during recording.
"""

from dataclasses import dataclass, field
from typing import List
import json
import os
import math

from simpleeval import SimpleEval, NameNotDefined, FunctionNotDefined


# Safe math functions exposed to expressions
SAFE_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "pow": pow,
}

SAFE_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class MathColumn:
    name: str
    expression: str
    description: str = ""

    def to_dict(self):
        return {"name": self.name, "expression": self.expression, "description": self.description}

    @classmethod
    def from_dict(cls, d):
        return cls(name=d["name"], expression=d["expression"], description=d.get("description", ""))


@dataclass
class MathConfig:
    columns: List[MathColumn] = field(default_factory=list)

    def get_column_names(self) -> List[str]:
        return [c.name for c in self.columns]

    def is_empty(self) -> bool:
        return len(self.columns) == 0

    def to_dict(self):
        return {"math_columns": [c.to_dict() for c in self.columns]}

    @classmethod
    def from_dict(cls, d):
        cols = [MathColumn.from_dict(item) for item in d.get("math_columns", [])]
        return cls(columns=cols)


# ── JSON persistence ──────────────────────────────────────────────────────────

def save_math_config(config: MathConfig, filepath: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(config.to_dict(), f, indent=4)


def load_math_config(filepath: str) -> MathConfig:
    with open(filepath, "r") as f:
        return MathConfig.from_dict(json.load(f))


# ── Safe evaluator ────────────────────────────────────────────────────────────

class MathEvaluator:
    """Wraps SimpleEval to safely evaluate user-defined math expressions."""

    def __init__(self, config: MathConfig):
        self.config = config
        self._eval = SimpleEval()
        self._eval.functions = SAFE_FUNCTIONS.copy()
        self._eval.names = SAFE_CONSTANTS.copy()

    def validate(self, available_columns: List[str]) -> tuple:
        """Test-evaluate all expressions with dummy values.

        Returns (True, "") on success, or (False, error_message) on failure.
        """
        seen_names = set()

        for col in self.config.columns:
            # Check for duplicate math column names
            if col.name in seen_names:
                return False, f"Duplicate math column name: '{col.name}'"
            seen_names.add(col.name)

            # Check for collision with instrument columns
            if col.name in available_columns:
                return False, f"Math column '{col.name}' conflicts with an existing column name"

        # Build dummy namespace: all instrument columns + prior math columns = 1.0
        dummy = SAFE_CONSTANTS.copy()
        for name in available_columns:
            dummy[name] = 1.0

        evaluator = SimpleEval()
        evaluator.functions = SAFE_FUNCTIONS.copy()

        for col in self.config.columns:
            evaluator.names = dummy.copy()
            try:
                evaluator.eval(col.expression)
            except NameNotDefined as e:
                return False, f"Math column '{col.name}': unknown variable — {e}"
            except FunctionNotDefined as e:
                return False, f"Math column '{col.name}': unknown function — {e}"
            except Exception as e:
                return False, f"Math column '{col.name}': {e}"
            # Allow later columns to reference this one
            dummy[col.name] = 1.0

        return True, ""

    def evaluate_row(self, row: dict) -> dict:
        """Evaluate all math columns against a data row.

        Non-numeric values in the row default to 0.0.
        Failed evaluations produce the string "ERROR".
        Columns evaluate in list order so column N can reference columns 1..N-1.
        """
        # Build numeric namespace from the row
        ns = SAFE_CONSTANTS.copy()
        for key, val in row.items():
            try:
                ns[key] = float(val)
            except (ValueError, TypeError):
                ns[key] = 0.0

        results = {}
        for col in self.config.columns:
            self._eval.names = ns.copy()
            try:
                result = self._eval.eval(col.expression)
                results[col.name] = result
                ns[col.name] = float(result)
            except Exception:
                results[col.name] = "ERROR"
                ns[col.name] = 0.0

        return results
