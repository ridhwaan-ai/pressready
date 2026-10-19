import json
import zipfile
import xml.dom.minidom as minidom

import pytest

from pressready.book import Book, BookError, Section
from pressready.epub import build_epub
from pressready.markdown import to_xhtml

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20


def sample_book():
    return Book(
        title="Tiny & Brave", author="A. Writer", subtitle="A Test",
        chapters=[Section("One", "# One\n\nHello *world* and **bold**.\n\n* * *\n\nAfter <break>."),
                  Section("Two", "# Two\n\n- a\n- b\n\n> quoted")],
        back_matter=[Section("About", "# About\n\nThe author.")],
    )


def test_markdown_basics():
    html = to_xhtml("# T\n\nA *b* & c.\n\n---\n\nNext")
    assert "<h1>" not in html
    assert "<em>b</em>" in html and "&amp;" in html
    assert 'class="scene-break"' in html
    assert "<p>Next</p>" in html


def test_epub_structure(tmp_path):
    out = tmp_path / "b.epub"
    build_epub(sample_book(), out, cover=PNG)
    z = zipfile.ZipFile(out)
    first = z.infolist()[0]
    assert first.filename == "mimetype"
    assert first.compress_type == zipfile.ZIP_STORED
    assert z.read("mimetype") == b"application/epub+zip"
    assert "OEBPS/content.opf" in z.read("META-INF/container.xml").decode()
    opf = z.read("OEBPS/content.opf").decode()
    assert 'version="3.0"' in opf and 'properties="nav"' in opf and 'properties="cover-image"' in opf
    names = set(z.namelist())
    # every manifest href exists, every xml part parses
    dom = minidom.parseString(opf)
    for item in dom.getElementsByTagName("item"):
        assert "OEBPS/" + item.getAttribute("href") in names
    for n in names:
        if n.endswith((".xhtml", ".opf", ".xml")):
            minidom.parseString(z.read(n))
    nav = z.read("OEBPS/nav.xhtml").decode()
    assert "c001.xhtml" in nav and "About" in nav
    ids = [i.getAttribute("id") for i in dom.getElementsByTagName("item")]
    assert all(r.getAttribute("idref") in ids for r in dom.getElementsByTagName("itemref"))


def test_epub_without_cover_and_bad_cover(tmp_path):
    build_epub(sample_book(), tmp_path / "a.epub")
    assert "cover-image" not in zipfile.ZipFile(tmp_path / "a.epub").read("OEBPS/content.opf").decode()
    with pytest.raises(BookError):
        build_epub(sample_book(), tmp_path / "x.epub", cover=b"nope")


def test_from_dir(tmp_path):
    (tmp_path / "book.json").write_text(json.dumps({"title": "T", "author": "A"}))
    (tmp_path / "01-start.md").write_text("# Start\n\nText.")
    (tmp_path / "02-end.md").write_text("Just text.")
    b = Book.from_dir(tmp_path)
    assert [c.title for c in b.chapters] == ["Start", "02 End"]


def test_from_dir_errors(tmp_path):
    with pytest.raises(BookError, match="book.json"):
        Book.from_dir(tmp_path)
    (tmp_path / "book.json").write_text(json.dumps({"title": "T", "author": "A"}))
    with pytest.raises(BookError, match="chapter"):
        Book.from_dir(tmp_path)
