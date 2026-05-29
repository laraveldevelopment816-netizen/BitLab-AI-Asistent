"""
FAQ loader — parsira `data/faq.md` po Markdown headerima i pruža keyword pretragu.

Claude će pozivati `get_faq(topic)`; ovaj modul vraća top-N najrelevantnijih sekcija.
Pravi rerank radi sam Claude na osnovu vraćenog teksta.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


_HEADER_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_WORD_RE = re.compile(r"\w+", re.UNICODE)


@dataclass
class FaqSection:
    title: str  # puna staza, npr. "Poslovanje > Informacije o firmi"
    headers: list[str] = field(default_factory=list)
    content: str = ""

    @property
    def search_text(self) -> str:
        return f"{self.title}\n{self.content}"

    def to_dict(self) -> dict:
        return {"title": self.title, "content": self.content}


def load_faq(path: Path) -> list[FaqSection]:
    """Parsira FAQ.md u flat listu sekcija sa nested header path-om."""
    text = path.read_text(encoding="utf-8")
    sections: list[FaqSection] = []
    stack: list[tuple[int, str]] = []  # (level, title)
    buf: list[str] = []

    def flush() -> None:
        if not stack:
            return
        content = "\n".join(buf).strip()
        if not content:
            return
        headers = [t for _, t in stack]
        sections.append(
            FaqSection(
                title=" > ".join(headers),
                headers=headers,
                content=content,
            )
        )

    for line in text.splitlines():
        m = _HEADER_RE.match(line)
        if m:
            flush()
            buf = []
            level = len(m.group(1))
            title = m.group(2).strip()
            # zatvori sve dublje ili jednake nivoe — ovaj ih zamjenjuje
            stack = [(lvl, t) for lvl, t in stack if lvl < level]
            stack.append((level, title))
        else:
            buf.append(line)

    flush()
    return sections


def _tokens(s: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(s) if len(w) > 2]


def search_faq(
    sections: Iterable[FaqSection],
    topic: str,
    top_k: int = 3,
) -> list[FaqSection]:
    """Jednostavan keyword scoring; Claude reranka semantički iz tool resulta."""
    query_tokens = _tokens(topic)
    if not query_tokens:
        return []

    scored: list[tuple[float, FaqSection]] = []
    for s in sections:
        title_lower = s.title.lower()
        content_lower = s.content.lower()
        score = 0.0
        for tok in query_tokens:
            # title hits su jako vredni
            if tok in title_lower:
                score += 5.0
            # frequency u sadržaju
            score += content_lower.count(tok) * 1.0
        if score > 0:
            scored.append((score, s))

    scored.sort(key=lambda x: -x[0])
    return [s for _, s in scored[:top_k]]
