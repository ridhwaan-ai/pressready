import json
import zipfile

from pypdf import PdfReader

from pressready.book import Book, Section
from pressready.epub import build_epub
from pressready.pdf import build_interior_pdf


def book(own):
    return Book(
        title="Zorbatron", author="A. Writer", own_front_matter=own,
        front_matter=[Section("Title Page", "# Title Page\n\nMyOwnTitleMarker"),
                      Section("Copyright", "# Copyright\n\nMyOwnRightsMarker")],
        chapters=[Section("One", "# One\n\n" + "Some text here. " * 40)],
    )


def test_epub_skips_generated_pages_when_own(tmp_path):
    build_epub(book(True), tmp_path / "a.epub")
    names = zipfile.ZipFile(tmp_path / "a.epub").namelist()
    assert "OEBPS/titlepage.xhtml" not in names and "OEBPS/copyright.xhtml" not in names
    build_epub(book(False), tmp_path / "b.epub")
    names = zipfile.ZipFile(tmp_path / "b.epub").namelist()
    assert "OEBPS/titlepage.xhtml" in names and "OEBPS/copyright.xhtml" in names


def test_pdf_has_no_generated_copyright_when_own(tmp_path):
    build_interior_pdf(book(True), tmp_path / "a.pdf")
    text = "".join(p.extract_text() or "" for p in PdfReader(str(tmp_path / "a.pdf")).pages)
    assert "All rights reserved" not in text and "MyOwnTitleMarker" in text
    first = PdfReader(str(tmp_path / "a.pdf")).pages[0].extract_text()
    assert "MyOwnTitleMarker" in first  # page 1 is the manuscript's own title page, not blank
    build_interior_pdf(book(False), tmp_path / "b.pdf")
    text = "".join(p.extract_text() or "" for p in PdfReader(str(tmp_path / "b.pdf")).pages)
    assert "All rights reserved" in text


def test_from_dir_flag(tmp_path):
    (tmp_path / "book.json").write_text(json.dumps({"title": "T", "author": "A", "own_front_matter": True}))
    (tmp_path / "01.md").write_text("# One\n\nText.")
    assert Book.from_dir(tmp_path).own_front_matter is True
