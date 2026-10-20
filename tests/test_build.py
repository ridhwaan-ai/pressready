import json
import zipfile

import pytest
from PIL import Image
from pypdf import PdfReader

from pressready import spine_width_in
from pressready.book import BookError
from pressready.build import build
from pressready.checklist import title_warnings


def make_manuscript(root):
    root.mkdir()
    (root / "book.json").write_text(json.dumps(
        {"title": "Tiny Brave", "author": "A. Writer", "description": "A small tale."}), encoding="utf-8")
    (root / "01-one.md").write_text("# One\n\nHello world.\n\n***\n\nSecond scene.", encoding="utf-8")
    (root / "02-two.md").write_text("# Two\n\nMore text here.", encoding="utf-8")


def test_title_warnings():
    assert title_warnings("Free Money") and title_warnings("The Bestseller")
    assert title_warnings("Tiny Brave") == []


def test_end_to_end(tmp_path):
    ms = tmp_path / "ms"
    make_manuscript(ms)
    art = tmp_path / "front.png"
    Image.new("RGB", (800, 1200), (30, 90, 160)).save(art)
    out = tmp_path / "out"
    cl = build(ms, art, out, trim="5x8", paper="cream", keywords=["tiny", "brave"])

    pages = cl["paperback"]["page_count"]
    interior = PdfReader(str(out / "interior.pdf"))
    assert len(interior.pages) == pages
    assert float(interior.pages[0].mediabox.width) == pytest.approx(5 * 72, abs=0.01)
    assert float(interior.pages[0].mediabox.height) == pytest.approx(8 * 72, abs=0.01)

    spine = spine_width_in(pages, "cream")
    assert cl["paperback"]["spine_width_in"] == spine
    wrap = PdfReader(str(out / "cover-wrap.pdf")).pages[0]
    assert float(wrap.mediabox.width) == pytest.approx((10 + 0.25 + spine) * 72, abs=0.01)
    assert float(wrap.mediabox.height) == pytest.approx(8.25 * 72, abs=0.01)

    with zipfile.ZipFile(out / "book.epub") as z:
        first = z.infolist()[0]
        assert first.filename == "mimetype" and first.compress_type == zipfile.ZIP_STORED
        assert "META-INF/container.xml" in z.namelist()

    saved = json.loads((out / "checklist.json").read_text(encoding="utf-8"))
    assert saved["ok"] is True and saved["files"]["kindle_epub"] == "book.epub"


def test_missing_cover(tmp_path):
    ms = tmp_path / "ms"
    make_manuscript(ms)
    with pytest.raises(BookError):
        build(ms, tmp_path / "nope.png", tmp_path / "out")
