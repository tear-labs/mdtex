"""IR -> LaTeX body."""
from __future__ import annotations

from .blocks import BulletList, HtmlTable, Paragraph, Placeholder, Section, parse_html_table
from .errors import MdtexError
from .inlines import inline_to_tex


def emit_body(
    sections: list[Section],
    fragments: dict[str, str],
    references_tex: str,
) -> str:
    pieces: list[str] = []
    for section in sections:
        if section.id == "references":
            pieces.append(references_tex)
            continue
        if section.heading is not None:
            pieces.append(
                f"\\section{{{inline_to_tex(section.heading)}}}\n"
                f"\\label{{sec:{section.id}}}"
            )
        for block in section.blocks:
            pieces.append(_emit_block(block, fragments))
    return "\n\n".join(piece for piece in pieces if piece)


def _emit_block(block, fragments: dict[str, str]) -> str:
    if isinstance(block, Paragraph):
        return inline_to_tex(block.text)
    if isinstance(block, BulletList):
        items = "\n".join(f"\\item {inline_to_tex(item)}" for item in block.items)
        return "\\begin{itemize}\n" + items + "\n\\end{itemize}"
    if isinstance(block, Placeholder):
        if block.name not in fragments:
            raise MdtexError(f"unknown fragment placeholder {{{{{block.name}}}}}")
        return fragments[block.name]
    if isinstance(block, HtmlTable):
        return _emit_table(block.html)
    raise MdtexError(f"unhandled block {block!r}")


def _emit_table(html_text: str) -> str:
    header, rows = parse_html_table(html_text)
    columns = len(header)
    label_width = 0.20
    value_width = round((0.94 - label_width) / max(1, columns - 1), 3)
    spec = (
        "@{}p{" + f"{label_width}\\linewidth" + "}"
        + ("p{" + f"{value_width}\\linewidth" + "}") * (columns - 1)
        + "@{}"
    )
    lines = [
        "\\begin{center}",
        "\\begin{tabular}{" + spec + "}",
        "\\toprule",
        " & ".join(
            "\\textbf{" + inline_to_tex(cell) + "}" if cell else ""
            for cell in header
        )
        + " \\\\",
        "\\midrule",
    ]
    for row in rows:
        cells = ["\\textbf{" + inline_to_tex(row[0]) + "}"] + [
            inline_to_tex(cell) for cell in row[1:]
        ]
        lines.append(" & ".join(cells) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{center}"]
    return "\n".join(lines)
