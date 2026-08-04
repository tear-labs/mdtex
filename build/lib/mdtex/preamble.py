"""Document skeleton for a single-column arXiv-style preprint."""
from __future__ import annotations

from .inlines import inline_to_tex


def _pdf_meta(text: str) -> str:
    """Plain-ASCII text for hyperref PDF metadata (no TeX macros)."""
    substitutions = {"–": "-", "—": "-", "×": "x", "…": "...", "’": "'"}
    for char, replacement in substitutions.items():
        text = text.replace(char, replacement)
    return "".join(char for char in text if ord(char) < 128)


def build_document(
    meta: dict[str, str],
    body_tex: str,
    *,
    title_key: str = "h1",
    thanks_tex: str = "",
    documentclass_options: tuple[str, ...] = ("11pt",),
    arxiv: bool = True,
    extra_preamble: str = "",
) -> str:
    title = inline_to_tex(meta[title_key])
    if thanks_tex:
        title += "\\thanks{" + thanks_tex + "}"
    author = inline_to_tex(meta.get("authors", ""))
    affiliation = meta.get("affiliation_name", "")
    if affiliation:
        author += "\\\\ " + inline_to_tex(affiliation)
    lines = [
        "\\documentclass[" + ",".join(documentclass_options) + "]{article}",
    ]
    if arxiv:
        lines.append("\\pdfoutput=1")
    lines += [
        "\\usepackage[margin=1in]{geometry}",
        "\\usepackage[T1]{fontenc}",
        "\\usepackage[utf8]{inputenc}",
        "\\usepackage{lmodern}",
        "\\usepackage{microtype}",
        "\\usepackage{amsmath,amssymb}",
        "\\usepackage{graphicx}",
        "\\usepackage{booktabs}",
        "\\usepackage[colorlinks=true,linkcolor=black,citecolor=blue,urlcolor=blue]{hyperref}",
        "\\hypersetup{pdftitle={" + _pdf_meta(meta.get(title_key, "")) + "},"
        + "pdfauthor={" + _pdf_meta(meta.get("authors", "")) + "}}",
    ]
    if extra_preamble:
        lines.append(extra_preamble)
    lines += [
        "",
        "\\title{" + title + "}",
        "\\author{" + author + "}",
        "\\date{" + inline_to_tex(meta.get("published", "")) + "}",
        "",
        "\\begin{document}",
        "\\maketitle",
    ]
    abstract = meta.get("abstract", "")
    if abstract:
        lines += [
            "",
            "\\begin{abstract}",
            inline_to_tex(abstract),
            "\\end{abstract}",
        ]
    lines += ["", body_tex, "", "\\end{document}", ""]
    return "\n".join(lines)
