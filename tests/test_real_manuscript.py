"""Regressions found by building a real KDP novel (The Mender of Thistlemarsh) on 2026-10-24."""
import json

from pypdf import PdfReader

from pressready.book import Book
from pressready.markdown import to_xhtml
from pressready.pdf import build_interior_pdf


def _book(tmp_path):
    (tmp_path / "book.json").write_text(json.dumps({"title": "T", "author": "A"}), encoding="utf-8")
    (tmp_path / "chapter-01.md").write_text("## Chapter One: A Week\n\nFirst line.\n\nSecond.", encoding="utf-8")
    (tmp_path / "front").mkdir()
    (tmp_path / "front" / "00.md").write_text('<div class="title-page">\n\n# Title Page\n\nBy A\n\n</div>\n',
                                              encoding="utf-8")
    return Book.from_dir(tmp_path)


def test_level2_opening_heading_is_the_chapter_title(tmp_path):
    book = _book(tmp_path)
    assert book.chapters[0].title == "Chapter One: A Week"
    assert "<h2>" not in to_xhtml(book.chapters[0].markdown)  # not printed twice


def test_raw_html_tag_lines_are_not_printed(tmp_path):
    book = _book(tmp_path)
    assert book.front_matter[0].title == "Title Page"
    assert "div" not in to_xhtml(book.front_matter[0].markdown)


def test_every_pdf_font_is_embedded_and_no_helvetica(tmp_path):
    book = _book(tmp_path)
    out = tmp_path / "interior.pdf"
    build_interior_pdf(book, out)
    for page in PdfReader(out).pages:
        fonts = page.get("/Resources", {}).get("/Font", {})
        for ref in fonts.values():
            f = ref.get_object()
            assert "Helvetica" not in str(f.get("/BaseFont"))
            desc = f.get("/FontDescriptor") or f.get("/DescendantFonts", [{}])[0].get_object().get("/FontDescriptor")
            desc = desc.get_object()
            assert any(k in desc for k in ("/FontFile", "/FontFile2", "/FontFile3")), f.get("/BaseFont")
