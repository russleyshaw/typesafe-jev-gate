from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "typesafe_jev_gate",
    ROOT / "__init__.py",
    submodule_search_locations=[str(ROOT)],
)
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["typesafe_jev_gate"] = MODULE
SPEC.loader.exec_module(MODULE)
