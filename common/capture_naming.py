"""Filename templating for oscilloscope captures.

A lab tech sweeping one variable (input voltage, ambient temperature, load)
takes the same measurement dozens of times, and the only thing that
distinguishes one capture from the next is the value of that variable. So the
capture name is built from a template plus a small set of user-named fields:

    template : {prefix}_Vin{Vin}_T{Temp}_{n:03d}
    fields   : prefix=psu_ripple, Vin=13.5, Temp=25
    result   : psu_ripple_Vin13.5_T25_007

The same fields become columns in the run CSV, so the filename and the row
always agree about which conditions produced the capture.
"""

import csv
import os
import re
import string
from datetime import datetime

# Tokens the template always understands, on top of whatever fields the user
# defines. Keep in sync with TOKEN_HELP below (shown in the tab's tooltip).
BUILTIN_TOKENS = ("date", "time", "datetime", "n", "model")

TOKEN_HELP = (
    "Built-in tokens:\n"
    "  {date}      2026-09-07\n"
    "  {time}      14_32_05\n"
    "  {datetime}  2026-09-07_14_32_05\n"
    "  {n}         capture number, {n:03d} zero-pads to 007\n"
    "  {model}     connected scope model\n\n"
    "Plus one token per field defined below, e.g. {Vin}."
)

DEFAULT_TEMPLATE = "{prefix}_{n:03d}"

# Anything that is awkward in a filename on either Linux or Windows.
_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_FIELD_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class TemplateError(ValueError):
    """Raised when a template references a token that has no value."""


def is_valid_field_name(name):
    """Field names double as format tokens, so they must be identifiers."""
    return bool(_FIELD_NAME.match(name or ""))


def sanitize_component(value):
    """Make a single value safe to embed in a filename.

    Illegal characters and whitespace collapse to underscores; leading and
    trailing dots and separators are trimmed so a field left blank cannot
    produce a hidden file or an empty path segment.
    """
    text = _ILLEGAL.sub("_", str(value))
    text = re.sub(r"\s+", "_", text).strip("._-")
    return text


def build_token_values(fields, n, model="", when=None):
    """Assemble the full token namespace for a render."""
    when = when or datetime.now()
    values = {
        "date": when.strftime("%Y-%m-%d"),
        "time": when.strftime("%H_%M_%S"),
        "datetime": when.strftime("%Y-%m-%d_%H_%M_%S"),
        "model": sanitize_component(model),
        "n": int(n),
    }
    # User fields win over built-ins only if they were named after one, which
    # is the user's call to make.
    for key, val in (fields or {}).items():
        values[key] = sanitize_component(val)
    return values


def render(template, fields, n, model="", when=None):
    """Render a capture name (no extension, no directory).

    Raises TemplateError for an unknown token or a malformed template, so the
    tab can show the problem before anything is written to disk.
    """
    values = build_token_values(fields, n, model, when)
    try:
        name = string.Formatter().vformat(template, (), _StrictTokens(values))
    except KeyError as e:
        available = ", ".join(sorted(values))
        raise TemplateError(
            f"Unknown token {{{e.args[0]}}} in template. Available: {available}") from e
    except (ValueError, IndexError) as e:
        raise TemplateError(f"Malformed template: {e}") from e

    name = sanitize_component(name)
    if not name:
        raise TemplateError("Template rendered to an empty filename")
    return name


class _StrictTokens(dict):
    """dict that reports the missing key rather than substituting a blank."""

    def __missing__(self, key):
        raise KeyError(key)


# A screenshot's real format isn't known until the scope answers (the X-series
# sends PNG, older Agilent models BMP), so reserving a name has to consider
# every extension the write might end up using.
IMAGE_EXTENSIONS = ("png", "bmp", "gif", "jpg", "tif")


def unique_path(path, extensions=None):
    """Return `path`, or the first `name_2.ext`-style variant that is free.

    The capture counter normally keeps names distinct; this only matters when
    a template leaves {n} out entirely.

    Args:
        extensions: if given, a stem counts as taken when a file exists with
            *any* of these extensions, not just the one in `path`. Pass
            IMAGE_EXTENSIONS when the writer may correct the extension.
    """
    stem, ext = os.path.splitext(path)

    def taken(candidate_stem):
        if extensions is None:
            return os.path.exists(candidate_stem + ext)
        return any(os.path.exists(f"{candidate_stem}.{e}") for e in extensions)

    if not taken(stem):
        return path
    i = 2
    while taken(f"{stem}_{i}"):
        i += 1
    return f"{stem}_{i}{ext}"


def next_index(csv_path):
    """Next capture number for a run, derived from the run CSV itself.

    The CSV is the record of what actually got captured, so counting its data
    rows survives an app restart and stays right if the user reopens an old
    run folder. Returns 1 for a run that has no CSV yet.
    """
    if not os.path.exists(csv_path):
        return 1
    with open(csv_path, "r", newline="") as f:
        rows = sum(1 for _ in csv.reader(f))
    # First row is the header.
    return max(1, rows)
