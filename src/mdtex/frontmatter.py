from __future__ import annotations

import re

from .errors import MdtexError


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    """Split a document into its front-matter mapping and body.

    Values may contain colons (titles, URLs, dates), so each line is split on
    the first colon only.
    """
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not match:
        raise MdtexError("document must start with a --- front matter block")
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, match.group(2)
