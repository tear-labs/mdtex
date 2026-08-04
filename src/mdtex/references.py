"""Parse the ``## References`` ordered list and emit thebibliography."""
from __future__ import annotations

import re

from .errors import MdtexError
from .inlines import inline_to_tex


def parse_references(body: str) -> dict[int, str]:
    """Return {number: raw markdown entry} from the References section."""
    parts = body.split("## References", 1)
    if len(parts) != 2:
        raise MdtexError("document needs a '## References' section")
    entries = {
        int(match.group(1)): match.group(2)
        for match in re.finditer(r"^(\d+)\.\s+(.+)$", parts[1], re.M)
    }
    if not entries:
        raise MdtexError("References section has no numbered entries")
    expected = list(range(1, max(entries) + 1))
    if sorted(entries) != expected:
        raise MdtexError(f"reference numbering has gaps: {sorted(entries)}")
    return entries


def emit_thebibliography(entries: dict[int, str]) -> str:
    lines = [f"\\begin{{thebibliography}}{{{len(entries)}}}"]
    for number in sorted(entries):
        lines.append(f"\\bibitem{{ref{number}}} {inline_to_tex(entries[number])}")
    lines.append("\\end{thebibliography}")
    return "\n".join(lines)
