import shutil
import subprocess
from pathlib import Path

import pytest

import mdtex
from test_golden import FIXTURE, fixture_config

BLANK_FIGURE = (
    "\\documentclass{article}\\usepackage[paperwidth=4in,paperheight=3in,margin=0.5in]"
    "{geometry}\\begin{document}(figure)\\end{document}"
)


@pytest.mark.skipif(shutil.which("latexmk") is None, reason="latexmk not installed")
def test_compiles(tmp_path: Path):
    blank_src = tmp_path / "blank.tex"
    blank_src.write_text(BLANK_FIGURE)
    subprocess.run(
        ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "blank.tex"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    figures = tmp_path / "paper" / "figures"
    figures.mkdir(parents=True)
    for index in range(1, 10):
        shutil.copy(tmp_path / "blank.pdf", figures / f"fig-{index}.pdf")

    result = mdtex.convert(FIXTURE, fixture_config())
    (tmp_path / "paper" / "main.tex").write_text(result.tex)
    proc = subprocess.run(
        ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
        cwd=tmp_path / "paper", check=False, capture_output=True, text=True,
    )
    log = (tmp_path / "paper" / "main.log").read_text(errors="replace")
    assert proc.returncode == 0, proc.stdout[-3000:] + log[-2000:]
    assert "Citation" not in log or "undefined" not in log.lower().split("citation")[1][:60]
    assert "There were undefined references" not in log
    assert "Missing character" not in log
    assert (tmp_path / "paper" / "main.pdf").exists()
