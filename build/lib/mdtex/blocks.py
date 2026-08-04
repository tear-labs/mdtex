"""Block-level parsing: protected body text -> intermediate representation."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

from .errors import MdtexError

_HEADING_RE = re.compile(r"(.+?)\s*\{#([\w-]+)\}\s*$")
_PLACEHOLDER_RE = re.compile(r"^\{\{([\w-]+)\}\}$")


@dataclass
class Paragraph:
    text: str


@dataclass
class BulletList:
    items: list[str]


@dataclass
class Placeholder:
    name: str


@dataclass
class HtmlTable:
    html: str


Block = Paragraph | BulletList | Placeholder | HtmlTable


@dataclass
class Section:
    id: str | None
    heading: str | None
    blocks: list[Block] = field(default_factory=list)


def parse_blocks(body: str) -> list[Section]:
    chunks = re.split(r"^## ", body, flags=re.M)
    sections = [Section(id=None, heading=None, blocks=_blocks(chunks[0]))]
    for chunk in chunks[1:]:
        heading_line, _, rest = chunk.partition("\n")
        match = _HEADING_RE.match(heading_line)
        if not match:
            raise MdtexError(f"section heading needs an {{#id}}: {heading_line!r}")
        heading, section_id = match.group(1), match.group(2)
        blocks = [] if section_id == "references" else _blocks(rest)
        sections.append(Section(id=section_id, heading=heading, blocks=blocks))
    return sections


def _blocks(text: str) -> list[Block]:
    blocks: list[Block] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue
        placeholder = _PLACEHOLDER_RE.match(stripped)
        if placeholder:
            blocks.append(Placeholder(placeholder.group(1)))
            index += 1
            continue
        if stripped.startswith('<div class="compare-wrap"'):
            collected = []
            while index < len(lines):
                collected.append(lines[index])
                if lines[index].strip() == "</div>":
                    index += 1
                    break
                index += 1
            blocks.append(HtmlTable("\n".join(collected)))
            continue
        if stripped.startswith("- "):
            items = []
            while index < len(lines) and lines[index].strip().startswith("- "):
                items.append(lines[index].strip()[2:])
                index += 1
            blocks.append(BulletList(items))
            continue
        paragraph = []
        while index < len(lines) and lines[index].strip():
            paragraph.append(lines[index].strip())
            index += 1
        blocks.append(Paragraph("\n".join(paragraph)))
    return blocks


class _TableAudit(HTMLParser):
    """Collect header cells and body rows from the compare-table HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.header: list[str] = []
        self.rows: list[list[str]] = []
        self._in_head = False
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "thead":
            self._in_head = True
        elif tag == "tr" and not self._in_head:
            self.rows.append([])
        elif tag in ("th", "td"):
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "thead":
            self._in_head = False
        elif tag in ("th", "td") and self._cell is not None:
            cell = "".join(self._cell).strip()
            if self._in_head:
                self.header.append(cell)
            elif self.rows:
                self.rows[-1].append(cell)
            self._cell = None

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)


def parse_html_table(html_text: str) -> tuple[list[str], list[list[str]]]:
    audit = _TableAudit()
    audit.feed(html_text)
    if not audit.header or not audit.rows:
        raise MdtexError("could not parse HTML comparison table")
    return audit.header, [row for row in audit.rows if row]
