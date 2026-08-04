# mdtex

Convert Tear Labs article-markdown into an arXiv-ready, single-column LaTeX
preprint. Zero runtime dependencies; fail-loud by design.

Licensed under Apache-2.0 (see [LICENSE](LICENSE) and [NOTICE](NOTICE)).
© Tear Labs Corp. — company-sponsored open research.

## The dialect

One markdown file drives both the web article and the paper:

- `---` front matter (`title`, `h1`, `authors`, `affiliation_name`,
  `published`, `abstract`, …); values may contain colons.
- `## Heading {#id}` sections. A `## References {#references}` section holds a
  plain ordered list `N. Authors [Title](url). Venue, Year.`
- `$…$` / `$$…$$` TeX math, passed through byte-for-byte (amsmath/amssymb
  commands only).
- `[@N]` citations; adjacent runs (`[@14][@15]`) merge into one `\cite`.
- `{{name}}` placeholders (figures, tables, …) resolved from a caller-supplied
  manifest of raw LaTeX fragments.
- Footnotes as `<sup class="fn"><a href="#fn-N">†</a></sup>` markers plus
  `<p class="footnote" id="fn-N">…</p>` bodies (which may themselves contain
  math, cites, and inline HTML) — merged into inline `\footnote{}`.
- Raw-HTML islands: `<table>` comparisons (→ booktabs) and
  `<pre class="bibtex">` blocks (→ verbatim).
- Inline markdown (`**bold**`, `*em*`, `` `code` ``, `[text](url)`), HTML
  entities, and Unicode punctuation/symbols mapped to TeX macros.

## API

```python
import mdtex

config = mdtex.Config(
    fragments={
        "toc": "",
        "fig-1": mdtex.figure("figures/fig-1.pdf", "Caption.", "fig:1"),
        # ... every {{placeholder}} in the document must be present
    },
    thanks_tex=r"Interactive version: \url{https://example.com/}.",
)
result = mdtex.convert(markdown_text, config)
Path("main.tex").write_text(result.tex)   # compile with latexmk -pdf
```

`convert` raises `MdtexError` on a cite with no reference entry, an unknown
placeholder, a leftover internal marker, or any non-ASCII character surviving
into the output — the document either converts fully or not at all.

Helpers: `mdtex.figure(...)` builds a figure fragment,
`mdtex.html_inline_to_tex(...)` converts limited inline HTML (e.g. captions),
`mdtex.escape_tex(...)` escapes a plain string.

## Escaping contract

Protection order is fixed: verbatim → display math → inline math → footnote
lift → citation runs. Inline structure is parsed before any escaping, and
escaping is applied only to literal text leaves in a single regex pass, so an
escape can never be re-escaped. Non-ASCII is mapped after escaping
(`–`→`--`, `×`→`\(\times\)`, `ℓ2`→`\(\ell_2\)`, `&nbsp;`→`~`, …).

## Tests

```bash
uv sync --extra dev
uv run pytest           # unit + golden + latexmk compile smoke (skipped if absent)
UPDATE_GOLDEN=1 uv run pytest tests/test_golden.py   # regenerate the golden .tex
```

The golden fixture is a real published article ("Naked Von Neumann", Tear
Labs 2026) exercising every construct above.
