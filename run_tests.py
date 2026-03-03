"""Test runner — invoke with: python run_tests.py

Runs the full test suite under tests/ using pytest.
Pass any extra pytest flags as arguments, e.g.:
    python run_tests.py -k math_columns
    python run_tests.py --tb=long
    python run_tests.py -x          # stop on first failure
"""

import sys
import pytest

PYTEST_ARGS = [
    "tests/",
    "-v",           # one line per test with pass/fail
    "--tb=short",   # compact tracebacks (use --tb=long for full detail)
    "--color=yes",
]

if __name__ == "__main__":
    # Any args passed on the command line are appended after the defaults
    extra = sys.argv[1:]
    sys.exit(pytest.main(PYTEST_ARGS + extra))
