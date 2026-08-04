from pathlib import Path

import pytest

from mdtex import MdtexError, escape_tex, html_inline_to_tex
from mdtex.blocks import BulletList, Paragraph, Placeholder, parse_blocks, parse_html_table
from mdtex.frontmatter import parse_front_matter
from mdtex.inlines import inline_to_tex
from mdtex.protect import TokenStore
from mdtex.references import emit_thebibliography, parse_references

FIXTURE = (Path(__file__).parent / "fixtures" / "article.md").read_text()


# ---- front matter


def test_front_matter_keeps_colons_in_values():
    meta, body = parse_front_matter(FIXTURE)
    assert meta["title"].startswith("Naked Von Neumann: VN Entropy")
    assert meta["citation_pdf_url"].startswith("https://")
    assert meta["citation_arxiv_id"] == ""
    assert body.lstrip().startswith("{{toc}}")


def test_front_matter_required():
    with pytest.raises(MdtexError):
        parse_front_matter("no front matter here")


# ---- protection round-trips


def test_math_round_trip_on_real_article():
    _, body = parse_front_matter(FIXTURE)
    store = TokenStore()
    protected = store.extract_math(body)
    assert "$" not in protected
    assert len(store.math_blocks) == 5
    assert any("\\underbrace" in block for block in store.math_blocks)
    restored = store.restore(protected)
    for block in store.math_blocks:
        assert block in restored


def test_verbatim_preserves_braces():
    store = TokenStore()
    text = '<pre class="bibtex"><code>@misc{x,\n  title = {T}\n}</code></pre>'
    protected = store.extract_verbatim(text)
    assert protected == "VERBATIM0MARKER"
    restored = store.restore(protected)
    assert "@misc{x," in restored and "\\begin{verbatim}" in restored


def test_cite_runs_merge_and_validate():
    store = TokenStore()
    out = store.tokenize_cites("JEPA[@14][@15] and[@1]", {1, 14, 15})
    assert out == "JEPACITE0MARKER andCITE1MARKER"
    assert store.restore(out) == "JEPA\\cite{ref14,ref15} and\\cite{ref1}"
    with pytest.raises(MdtexError):
        store.tokenize_cites("[@99]", {1})


def test_footnote_lift_real_article():
    _, body = parse_front_matter(FIXTURE)
    store = TokenStore()
    body = store.extract_math(body)
    body, notes = store.lift_footnotes(body)
    assert len(notes) == 6
    assert '<p class="footnote"' not in body
    assert "<sup" not in body
    assert body.count("FOOTNOTE") == 6
    # fn-2 body keeps its math tokens and inline code
    joined = "\n".join(notes.values())
    assert "MATHINLINE" in joined
    assert "torch.linalg.eigvalsh" in joined
    # symbols stripped
    for raw in notes.values():
        assert not raw.startswith(("†", "‡", "§", "‖", "¶"))


# ---- escaping


def test_single_pass_escape_every_special():
    assert escape_tex("50% & #1_a {b} $2 ^") == "50\\% \\& \\#1\\_a \\{b\\} \\$2 \\textasciicircum{}"
    assert escape_tex("~31% more") == "\\(\\sim\\)31\\% more"
    assert escape_tex("a\\b") == "a\\textbackslash{}b"


def test_unicode_map():
    assert escape_tex("3–6× less") == "3--6\\(\\times\\) less"
    assert escape_tex("ℓ2-normalized") == "\\(\\ell_2\\)-normalized"
    assert escape_tex("326.4 ± 2.3") == "326.4 \\(\\pm\\) 2.3"
    assert escape_tex("λ 0.02") == "\\(\\lambda\\) 0.02"
    assert escape_tex("“naked”") == "``naked''"


def test_entities_before_escaping():
    assert escape_tex("Dieng, A.&nbsp;B.") == "Dieng, A.~B."
    assert escape_tex("a&amp;b") == "a\\&b"


def test_inline_structures():
    assert inline_to_tex("**bold** and __also__") == "\\textbf{bold} and \\textbf{also}"
    assert inline_to_tex("`data/results.json`") == "\\texttt{data/results.json}"
    assert (
        inline_to_tex("[github.com/x](https://github.com/x)")
        == "\\href{https://github.com/x}{github.com/x}"
    )
    assert inline_to_tex("<code>a_b</code>") == "\\texttt{a\\_b}"
    assert inline_to_tex("<em>weaker</em>") == "\\emph{weaker}"


def test_html_inline_helper():
    assert html_inline_to_tex('<span class="fig-num">Figure 1.</span> rest') == "Figure 1. rest"
    assert html_inline_to_tex('<a href="https://x.y">link</a>') == "\\href{https://x.y}{link}"


# ---- blocks


def test_blocks_real_article_sections():
    _, body = parse_front_matter(FIXTURE)
    store = TokenStore()
    body = store.extract_verbatim(body)
    body = store.extract_math(body)
    body, _ = store.lift_footnotes(body)
    sections = parse_blocks(body)
    ids = [section.id for section in sections]
    assert ids == [
        None, "introduction", "objective", "faster", "stronger",
        "geometry", "discussion", "appendix", "references",
    ]
    intro = sections[1]
    assert any(isinstance(block, BulletList) for block in intro.blocks)
    assert any(isinstance(block, Paragraph) for block in intro.blocks)
    placeholders = [
        block.name
        for section in sections
        for block in section.blocks
        if isinstance(block, Placeholder)
    ]
    assert placeholders[0] == "toc"
    assert set(placeholders) >= {f"fig-{i}" for i in range(1, 10)} | {"table-1", "provenance"}


def test_compare_table_parses():
    _, body = parse_front_matter(FIXTURE)
    start = body.index('<div class="compare-wrap">')
    end = body.index("</div>", start) + len("</div>")
    header, rows = parse_html_table(body[start:end])
    assert header == ["", "VN entropy", "SIGReg"]
    assert len(rows) == 4
    assert rows[0][0] == "What is shaped"


# ---- references


def test_references_parse_and_emit():
    _, body = parse_front_matter(FIXTURE)
    refs = parse_references(body)
    assert sorted(refs) == list(range(1, 25))
    tex = emit_thebibliography(refs)
    assert tex.count("\\bibitem{ref") == 24
    # ref 3 has two links
    entry3 = [line for line in tex.splitlines() if "\\bibitem{ref3}" in line][0]
    assert entry3.count("\\href{") == 2
    # nbsp initials become ties
    assert "A.~B." in tex
