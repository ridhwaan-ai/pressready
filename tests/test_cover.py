import pytest
from PIL import Image
from pypdf import PdfReader

from pressready import spine_width_in
from pressready.book import Book, BookError, Section
from pressready.cover import wrap_dimensions, build_wrap_cover


def book():
    return Book(title="Tiny Brave", author="A. Writer", chapters=[Section("One", "# One\n\nText.")])


@pytest.fixture
def art(tmp_path):
    p = tmp_path / "front.png"
    Image.new("RGB", (1000, 1600), (200, 60, 60)).save(p)
    return p


@pytest.mark.parametrize("paper", ["white", "cream"])
def test_wrap_mediabox_and_spine(tmp_path, art, paper):
    out = tmp_path / "wrap.pdf"
    d = build_wrap_cover(book(), art, out, pages=200, trim="6x9", paper=paper, back_text="Blurb here.")
    spine = spine_width_in(200, paper)
    assert d["spine"] == spine
    expected_w = 0.125 * 2 + 12 + spine
    page = PdfReader(str(out)).pages[0]
    assert float(page.mediabox.width) == pytest.approx(expected_w * 72, abs=0.01)
    assert float(page.mediabox.height) == pytest.approx((9 + 0.25) * 72, abs=0.01)
    assert d["spine_text_drawn"] is True
    assert "Blurb" in page.extract_text()


def test_no_spine_text_on_thin_book(tmp_path, art):
    d = build_wrap_cover(book(), art, tmp_path / "w.pdf", pages=60)
    assert d["spine_text_allowed"] is False and d["spine_text_drawn"] is False


def test_cream_spine_wider_than_white():
    assert wrap_dimensions("5x8", 300, "cream")["spine"] > wrap_dimensions("5x8", 300, "white")["spine"]


def test_errors(tmp_path, art):
    with pytest.raises(BookError):
        wrap_dimensions("5x8", 10)
    with pytest.raises(BookError):
        wrap_dimensions("5x8", 100, "glossy")
    with pytest.raises(BookError):
        build_wrap_cover(book(), tmp_path / "missing.png", tmp_path / "w.pdf", pages=100)
    bad = tmp_path / "bad.png"
    bad.write_text("not an image")
    with pytest.raises(BookError):
        build_wrap_cover(book(), bad, tmp_path / "w.pdf", pages=100)
