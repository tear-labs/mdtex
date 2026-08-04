"""mdtex — Tear Labs article-markdown to arXiv-ready LaTeX.

The dialect (front matter, ``## Heading {#id}`` sections, ``$``/``$$`` TeX
math, ``[@N]`` citations against a ``## References`` ordered list,
``{{placeholder}}`` figures, HTML footnotes/tables) is converted into a
single-column article-class preprint. Callers supply raw-LaTeX fragments for
each placeholder; everything else is automatic. Fail-loud by design: unknown
cites, unknown placeholders, leftover markers, or non-ASCII output all raise.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .blocks import parse_blocks
from .emit import emit_body
from .errors import MdtexError
from .frontmatter import parse_front_matter
from .inlines import escape_tex, html_inline_to_tex, inline_to_tex
from .preamble import build_document
from .protect import TokenStore
from .references import emit_thebibliography, parse_references

__all__ = [
    "Config",
    "MdtexError",
    "Result",
    "convert",
    "escape_tex",
    "figure",
    "html_inline_to_tex",
]


@dataclass(frozen=True)
class Config:
    fragments: dict[str, str] = field(default_factory=dict)
    title_key: str = "h1"
    thanks_tex: str = ""
    documentclass_options: tuple[str, ...] = ("11pt",)
    arxiv: bool = True
    extra_preamble: str = ""


@dataclass(frozen=True)
class Result:
    tex: str
    body_tex: str
    meta: dict[str, str]
    graphics: tuple[str, ...]


def figure(
    path: str,
    caption_tex: str,
    label: str,
    width: float = 1.0,
    placement: str = "t",
) -> str:
    """Raw-LaTeX figure fragment for the placeholder manifest."""
    return (
        f"\\begin{{figure}}[{placement}]\n"
        "\\centering\n"
        f"\\includegraphics[width={width}\\linewidth]{{{path}}}\n"
        f"\\caption{{{caption_tex}}}\n"
        f"\\label{{{label}}}\n"
        "\\end{figure}"
    )


def convert(md_text: str, config: Config | None = None) -> Result:
    config = config or Config()
    meta, body = parse_front_matter(md_text)
    references = parse_references(body)
    known = set(references)

    store = TokenStore()
    body = store.extract_verbatim(body)
    body = store.extract_math(body)
    body, raw_notes = store.lift_footnotes(body)
    body = store.tokenize_cites(body, known)
    for index, raw_body in raw_notes.items():
        store.footnotes[index] = inline_to_tex(store.tokenize_cites(raw_body, known))

    sections = parse_blocks(body)
    body_tex = emit_body(sections, config.fragments, emit_thebibliography(references))
    body_tex = store.restore(body_tex)

    tex = build_document(
        meta,
        body_tex,
        title_key=config.title_key,
        thanks_tex=config.thanks_tex,
        documentclass_options=config.documentclass_options,
        arxiv=config.arxiv,
        extra_preamble=config.extra_preamble,
    )
    try:
        tex.encode("ascii")
    except UnicodeEncodeError as error:
        offset = error.start
        context = tex[max(0, offset - 40) : offset + 40]
        raise MdtexError(
            f"non-ASCII character {tex[offset]!r} survived conversion near: {context!r}"
        ) from None

    graphics = tuple(re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}", tex))
    return Result(tex=tex, body_tex=body_tex, meta=meta, graphics=graphics)
