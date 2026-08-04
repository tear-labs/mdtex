"""Inline markdown/HTML -> LaTeX with leaf-only escaping.

The invariant: escaping is applied only to literal text *leaves*, after all
inline structure (links, code, bold, emphasis) has been parsed out and after
protected spans (math, cites, footnotes) have been tokenized. The escape pass
is a single-pass regex, so an escape it produces can never be re-escaped.
Non-ASCII characters are then mapped to TeX macros; convert() asserts the
final document is pure ASCII so unmapped characters fail loudly.
"""
from __future__ import annotations

import html
import re

# Single-pass escape of LaTeX-active ASCII characters. Every literal tilde in
# the dialect means "approximately", hence \(\sim\) rather than a tie.
_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\(\sim\)",
    "^": r"\textasciicircum{}",
}
_ESCAPE_RE = re.compile(r"[\\&%$#_{}~^]")

# Multi-character sequences first, then single characters.
_UNICODE_PAIRS = [
    ("ℓ₂", r"\(\ell_2\)"),  # ℓ₂
    ("ℓ2", r"\(\ell_2\)"),  # ℓ2
]
_UNICODE_MAP = {
    " ": "~",  # nbsp -> tie
    " ": r"\,",  # thin space
    "–": "--",
    "—": "---",
    "‘": "`",
    "’": "'",
    "“": "``",
    "”": "''",
    "…": r"\dots{}",
    "×": r"\(\times\)",
    "≈": r"\(\approx\)",
    "±": r"\(\pm\)",
    "ℓ": r"\(\ell\)",
    "λ": r"\(\lambda\)",
    "ρ": r"\(\rho\)",
    "β": r"\(\beta\)",
    "→": r"\(\rightarrow\)",
    "·": r"\(\cdot\)",
    "≤": r"\(\le\)",
    "≥": r"\(\ge\)",
    "°": r"\(^\circ\)",
}


def _leaf(text: str) -> str:
    """Escape one literal text leaf (no inline structure inside)."""
    text = html.unescape(text)
    text = re.sub(r'"([^"\n]+)"', r"``\1''", text)
    text = _ESCAPE_RE.sub(lambda m: _ESCAPES[m.group(0)], text)
    for pair, tex in _UNICODE_PAIRS:
        text = text.replace(pair, tex)
    for char, tex in _UNICODE_MAP.items():
        text = text.replace(char, tex)
    return text


def _escape_url(url: str) -> str:
    return url.replace("%", r"\%").replace("#", r"\#")


# Inline structure, tried in order at each position.
_TOKENS = [
    (re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)"), "link"),
    (re.compile(r"`([^`]+)`"), "code"),
    (re.compile(r"<code>(.*?)</code>", re.S), "code"),
    (re.compile(r"\*\*(.+?)\*\*", re.S), "bold"),
    (re.compile(r"__(.+?)__", re.S), "bold"),
    (re.compile(r"<(?:b|strong)>(.*?)</(?:b|strong)>", re.S), "bold"),
    (re.compile(r"\*([^*\n]+)\*"), "emph"),
    (re.compile(r"<(?:em|i)>(.*?)</(?:em|i)>", re.S), "emph"),
]


def inline_to_tex(text: str) -> str:
    """Convert one inline run (a paragraph, list item, caption, cell)."""
    out: list[str] = []
    pos = 0
    while pos < len(text):
        best: tuple[int, re.Match, str] | None = None
        for pattern, kind in _TOKENS:
            match = pattern.search(text, pos)
            if match and (best is None or match.start() < best[0]):
                best = (match.start(), match, kind)
        if best is None:
            out.append(_leaf(text[pos:]))
            break
        start, match, kind = best
        out.append(_leaf(text[pos:start]))
        if kind == "link":
            out.append(
                "\\href{" + _escape_url(match.group(2)) + "}{"
                + inline_to_tex(match.group(1)) + "}"
            )
        elif kind == "code":
            out.append("\\texttt{" + _leaf(html.unescape(match.group(1))) + "}")
        elif kind == "bold":
            out.append("\\textbf{" + inline_to_tex(match.group(1)) + "}")
        else:
            out.append("\\emph{" + inline_to_tex(match.group(1)) + "}")
        pos = match.end()
    return "".join(out)


def html_inline_to_tex(html_text: str) -> str:
    """Public helper: limited inline HTML (captions, footnote bodies) -> TeX."""
    html_text = re.sub(r"<span[^>]*>(.*?)</span>", r"\1", html_text, flags=re.S)
    html_text = re.sub(r'<a href="([^"]+)">(.*?)</a>', r"[\2](\1)", html_text, flags=re.S)
    html_text = re.sub(r"<br\s*/?>", " ", html_text)
    return inline_to_tex(html_text)


def escape_tex(text: str) -> str:
    """Public helper: escape a plain string with no inline structure."""
    return _leaf(text)
