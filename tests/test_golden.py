import os
from pathlib import Path

import mdtex

GOLDEN = Path(__file__).parent / "golden" / "main.tex"
FIXTURE = (Path(__file__).parent / "fixtures" / "article.md").read_text()


def fixture_config() -> mdtex.Config:
    fragments = {"toc": ""}
    for index in range(1, 10):
        fragments[f"fig-{index}"] = mdtex.figure(
            f"figures/fig-{index}.pdf", f"Figure {index} caption.", f"fig:{index}"
        )
    fragments["table-1"] = (
        "\\begin{table}[t]\\centering\\begin{tabular}{@{}ll@{}}\\toprule\n"
        "Domain & VN \\\\\n\\midrule\nstub & 0 \\\\\n\\bottomrule\\end{tabular}"
        "\\caption{Stub.}\\label{tab:modalities}\\end{table}"
    )
    fragments["provenance"] = "\\paragraph{Provenance.} Stub."
    return mdtex.Config(
        fragments=fragments,
        thanks_tex="Interactive version: \\url{https://research.tearlabs.ai/__naked-vn/}.",
    )


def test_golden():
    result = mdtex.convert(FIXTURE, fixture_config())
    if os.environ.get("UPDATE_GOLDEN"):
        GOLDEN.write_text(result.tex)
    assert GOLDEN.exists(), "golden missing — run UPDATE_GOLDEN=1 pytest tests/test_golden.py"
    assert result.tex == GOLDEN.read_text()
    assert result.tex.count("\\bibitem{ref") == 24
    assert result.tex.count("\\footnote{") == 6
    assert result.tex.count("\\cite{") >= 20
    assert result.tex.count("\\begin{equation*}") == 5
    assert "\\begin{verbatim}" in result.tex
    assert len(result.graphics) == 9
