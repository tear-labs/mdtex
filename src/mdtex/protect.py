"""Token protection: carve out spans Markdown/escaping must never touch.

Order matters and is fixed by convert(): verbatim -> display math -> inline
math -> footnotes -> citations. Each protected span becomes an opaque ASCII
marker (``MATHBLOCK0MARKER``) that survives block parsing, inline conversion,
and escaping untouched, and is expanded back to LaTeX at the very end.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .errors import MdtexError

MARKER_RE = re.compile(r"(VERBATIM|MATHBLOCK|MATHINLINE|FOOTNOTE|CITE)(\d+)MARKER")

_FOOTNOTE_BODY_RE = re.compile(
    r'[ \t]*<p class="footnote" id="fn-(\d+)">(.*?)</p>\n?', re.S
)
_FOOTNOTE_MARK_RE = re.compile(
    r'<sup class="fn"><a href="#fn-(\d+)">[^<]*</a></sup>'
)
_FOOTNOTE_SYMBOL_RE = re.compile(r"^[\u2020\u2021\u00a7\u2016\u00b6*]+\s*")


@dataclass
class TokenStore:
    """Holds protected spans and expands them back after emission."""

    verbatim: list[str] = field(default_factory=list)
    math_blocks: list[str] = field(default_factory=list)
    math_inlines: list[str] = field(default_factory=list)
    footnotes: dict[int, str] = field(default_factory=dict)  # marker index -> body tex
    cites: list[list[int]] = field(default_factory=list)

    def extract_verbatim(self, text: str) -> str:
        def token(match: re.Match) -> str:
            self.verbatim.append(match.group(1))
            return f"VERBATIM{len(self.verbatim) - 1}MARKER"

        return re.sub(
            r'<pre class="bibtex"><code>(.*?)</code></pre>', token, text, flags=re.S
        )

    def extract_math(self, text: str) -> str:
        def block(match: re.Match) -> str:
            self.math_blocks.append(match.group(1).strip())
            return f"MATHBLOCK{len(self.math_blocks) - 1}MARKER"

        def inline(match: re.Match) -> str:
            self.math_inlines.append(match.group(1))
            return f"MATHINLINE{len(self.math_inlines) - 1}MARKER"

        text = re.sub(r"\$\$(.+?)\$\$", block, text, flags=re.S)
        return re.sub(r"\$(.+?)\$", inline, text)

    def lift_footnotes(self, text: str) -> tuple[str, dict[int, str]]:
        """Remove footnote paragraphs; replace their markers with tokens.

        Returns the new text and a map of marker index -> raw body (still
        containing math/cite markup, converted later by the caller).
        """
        bodies: dict[str, str] = {}

        def collect(match: re.Match) -> str:
            bodies[match.group(1)] = _FOOTNOTE_SYMBOL_RE.sub("", match.group(2).strip())
            return ""

        text = _FOOTNOTE_BODY_RE.sub(collect, text)

        raw_bodies: dict[int, str] = {}

        def token(match: re.Match) -> str:
            note_id = match.group(1)
            if note_id not in bodies:
                raise MdtexError(f"footnote marker #fn-{note_id} has no body")
            index = len(raw_bodies)
            raw_bodies[index] = bodies.pop(note_id)
            return f"FOOTNOTE{index}MARKER"

        text = _FOOTNOTE_MARK_RE.sub(token, text)
        if bodies:
            raise MdtexError(f"footnote bodies without markers: fn-{sorted(bodies)}")
        return text, raw_bodies

    def tokenize_cites(self, text: str, known: set[int]) -> str:
        def token(match: re.Match) -> str:
            numbers = [int(n) for n in re.findall(r"\[@(\d+)\]", match.group(0))]
            missing = [n for n in numbers if n not in known]
            if missing:
                raise MdtexError(f"citation [@{missing[0]}] has no reference entry")
            self.cites.append(numbers)
            return f"CITE{len(self.cites) - 1}MARKER"

        return re.sub(r"(?:\[@\d+\])+", token, text)

    def restore(self, tex: str) -> str:
        """Expand all markers to LaTeX, innermost-out, until none remain."""
        replacements = {
            "VERBATIM": lambda i: "\\begin{verbatim}\n"
            + self.verbatim[i]
            + "\n\\end{verbatim}",
            "MATHBLOCK": lambda i: "\\begin{equation*}\n"
            + self.math_blocks[i]
            + "\n\\end{equation*}",
            "MATHINLINE": lambda i: "$" + self.math_inlines[i] + "$",
            "FOOTNOTE": lambda i: "\\footnote{" + self.footnotes[i] + "}",
            "CITE": lambda i: "\\cite{"
            + ",".join(f"ref{n}" for n in self.cites[i])
            + "}",
        }
        for _ in range(10):
            expanded = MARKER_RE.sub(
                lambda m: replacements[m.group(1)](int(m.group(2))), tex
            )
            if expanded == tex:
                break
            tex = expanded
        if MARKER_RE.search(tex):
            raise MdtexError("unresolved token marker in emitted LaTeX")
        return tex
