"""Book model: metadata plus Markdown sections."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


class BookError(ValueError):
    """Raised for input problems; the message says exactly what to fix."""


@dataclass
class Section:
    title: str
    markdown: str


@dataclass
class Book:
    title: str
    author: str
    subtitle: str = ""
    series: str = ""
    language: str = "en"
    description: str = ""
    rights: str = ""
    identifier: str = ""
    chapters: list[Section] = field(default_factory=list)
    front_matter: list[Section] = field(default_factory=list)
    back_matter: list[Section] = field(default_factory=list)

    def validate(self) -> None:
        if not self.title.strip():
            raise BookError("title must not be empty")
        if not self.author.strip():
            raise BookError("author must not be empty")
        if not self.chapters:
            raise BookError("book needs at least one chapter (a .md file)")

    @classmethod
    def from_dir(cls, path: str | Path) -> "Book":
        """Load a manuscript folder.

        Layout: book.json (title, author, optional subtitle/series/language/description/rights/identifier),
        chapter files *.md sorted by name, optional front/*.md and back/*.md.
        A section title is its first '# ' heading, else the file name.
        """
        root = Path(path)
        meta_file = root / "book.json"
        if not meta_file.is_file():
            raise BookError(f"missing {meta_file}: create it with at least 'title' and 'author'")
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise BookError(f"book.json is not valid JSON: {e}") from e
        for key in ("title", "author"):
            if not str(meta.get(key, "")).strip():
                raise BookError(f"book.json is missing required field '{key}'")
        known = {"title", "author", "subtitle", "series", "language", "description", "rights", "identifier"}
        book = cls(**{k: str(v) for k, v in meta.items() if k in known})
        book.chapters = _load_sections(root, "*.md")
        book.front_matter = _load_sections(root / "front", "*.md")
        book.back_matter = _load_sections(root / "back", "*.md")
        book.validate()
        return book


def _load_sections(folder: Path, pattern: str) -> list[Section]:
    if not folder.is_dir():
        return []
    out = []
    for f in sorted(folder.glob(pattern)):
        text = f.read_text(encoding="utf-8")
        m = re.search(r"^#\s+(.+?)\s*$", text, re.M)
        title = m.group(1) if m else f.stem.replace("-", " ").replace("_", " ").strip().title()
        out.append(Section(title, text))
    return out
