"""One-call orchestrator: manuscript folder + cover image -> EPUB, interior PDF, wrap cover, checklist."""
from __future__ import annotations

import json
from pathlib import Path

from .book import Book, BookError
from .checklist import build_checklist
from .cover import build_wrap_cover
from .epub import build_epub
from .pdf import build_interior_pdf


def build(book: Book | str | Path, cover_image: str | Path, out_dir: str | Path,
          trim: str = "5.5x8.5", paper: str = "white", keywords: list[str] | None = None,
          back_text: str = "") -> dict:
    """Build all deliverables into out_dir and return the checklist dict."""
    if not isinstance(book, Book):
        book = Book.from_dir(book)
    book.validate()
    cover_image = Path(cover_image)
    if not cover_image.is_file():
        raise BookError(f"front cover image not found: {cover_image}")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    epub_path, interior_path, wrap_path = out / "book.epub", out / "interior.pdf", out / "cover-wrap.pdf"
    build_epub(book, epub_path, cover=cover_image.read_bytes())
    pages = build_interior_pdf(book, interior_path, trim=trim)
    d = build_wrap_cover(book, cover_image, wrap_path, pages=pages, trim=trim, paper=paper,
                         back_text=back_text or book.description)
    checklist = build_checklist(
        book, pages=pages, trim=trim, paper=paper, spine_in=d["spine"],
        wrap_size_in=(d["width"], d["height"]), keywords=keywords,
        files={"kindle_epub": epub_path.name, "interior_pdf": interior_path.name,
               "cover_pdf": wrap_path.name})
    (out / "checklist.json").write_text(json.dumps(checklist, indent=2), encoding="utf-8")
    return checklist
