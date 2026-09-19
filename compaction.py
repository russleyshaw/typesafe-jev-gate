"""Cheap transcript hygiene that runs before Hermes's LLM compactor.

Tool output often contains ephemeral progress/spinner lines that have no value after
execution.  Keep this pass deterministic and local: it must never spend a Jev/API
request, and it must never remove substantive output.
"""

from __future__ import annotations

import re
from typing import Any

# These patterns intentionally require a line to be *only* an indicator.  They
# are deliberately broad: tool status such as ``Process exited with code 0``
# and ``Running tests`` is transient context, not task evidence. A line such as
# ``Processing 12 files`` remains useful evidence and is retained.
_STATUS_WORDS = (
    r"working|processing|loading|thinking|waiting|running|searching|indexing|"
    r"executing|initializing|starting|stopping|finishing|retrying|checking|"
    r"scanning|building|compiling|installing|downloading|uploading"
)
_USELESS_LINE = re.compile(
    rf"^\s*(?:"
    rf"(?:[\u2500-\u257f\u2580-\u259f\u2800-\u28ff]|[|/\\-])\s*(?:{_STATUS_WORDS})"
    rf"(?:\s+\w+)?(?:\.+|…)?"
    rf"|(?:{_STATUS_WORDS})(?:\s+\w+)?(?:\.+|…)?"
    rf"|(?:progress|operation)\s*[:：-]?\s*\[\s*[=#>.-]+\s*\]\s*\d{{1,3}}%?"
    rf"|\[\s*[=#>.-]+\s*\]\s*\d{{1,3}}%"
    rf"|\d{{1,3}}%\s*(?:complete|completed|done)"
    rf"|(?:process|command)\s+(?:started|running|finished|completed)(?:\s*[:：-]?\s+.*)?"
    rf"|(?:process|command)\s+exited\s+with\s+(?:code\s+)?0"
    rf"|(?:exit|return)\s*(?:code\s*)?[:：-]?\s*0"
    rf"|(?:done|complete|completed|success|successful|ok|all done|no changes)\s*[.!✓✔]*"
    rf"|[✓✔]\s*(?:done|complete|completed|success|successful)\s*[.!]*"
    r")\s*$",
    re.IGNORECASE,
)
_ANSI = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")


def compact_tool_result(result: Any) -> Any:
    """Remove standalone ephemeral indicator lines from a textual tool result."""
    if not isinstance(result, str) or not result:
        return result

    normalized = _ANSI.sub("", result)
    lines = normalized.splitlines()
    kept = [line for line in lines if not _USELESS_LINE.fullmatch(line)]
    if len(kept) == len(lines):
        return result

    # Avoid leaving a large blank gutter where a progress stream was removed.
    output: list[str] = []
    blank_seen = False
    for line in kept:
        if not line.strip():
            if blank_seen:
                continue
            blank_seen = True
        else:
            blank_seen = False
        output.append(line)
    compacted = "\n".join(output)
    if result.endswith(("\n", "\r")) and compacted:
        compacted += "\n"
    return compacted


__all__ = ["compact_tool_result"]
