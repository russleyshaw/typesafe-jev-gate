from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location(
    "typesafe_jev_gate",
    ROOT / "__init__.py",
    submodule_search_locations=[str(ROOT)],
)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules["typesafe_jev_gate"] = module
spec.loader.exec_module(module)

# ruff: noqa: E402, I001
from typesafe_jev_gate.evaluation import evaluate
from typesafe_jev_gate.metrics import report


if __name__ == "__main__":
    print({"evaluation": evaluate(), "telemetry": report()})
