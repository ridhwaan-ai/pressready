import pytest
from pypdf import PdfReader

from pressready.book import Book, BookError, Section
from pressready.pdf import MIN_PAGES, build_interior_pdf, parse_trim


def sample_book(chapters=2):
    body = "\n\n".join(f"Paragraph {i} with *emphasis* and **bold** text. " * 6 for i in range(8))
    return Book(
        title="Tiny & Brave", author="A. Writer", subtitle="A Test",
        chapters=[Section(f"Chapter {n}", f"# Chapter {n}\n\n{body}\n\n* * *\n\n{body}") for n in range(1, chapters + 1)],
    )


@pytest.mark.parametrize("trim", ["5x8", "5.5x8.5", "6x9", "8.5x11"])
def test_exact_page_size_even_and_min_pages(tmp_path, trim):
    out = tmp_path / "interior.pdf"
    pages = build_interior_pdf(sample_book(), out, trim=trim)
    reader = PdfReader(str(out))
    w, h = parse_trim(trim)
    assert len(reader.pages) == pages
    assert pages >= MIN_PAGES and pages % 2 == 0
    for p in reader.pages:
        assert float(p.mediabox.width) == pytest.approx(w * 72, abs=0.01)
        assert float(p.mediabox.height) == pytest.approx(h * 72, abs=0.01)


def test_chapters_start_on_odd_pages_and_fonts_embedded(tmp_path):
    out = tmp_path / "interior.pdf"
    build_interior_pdf(sample_book(3), out)
    reader = PdfReader(str(out))
    starts = [i + 1 for i, p in enumerate(reader.pages) if "Chapter" in (p.extract_text() or "")[:40]]
    assert len(starts) >= 3
    assert all(n % 2 == 1 for n in starts)
    assert b"/FontFile2" in out.read_bytes()


def test_running_heads(tmp_path):
    out = tmp_path / "interior.pdf"
    build_interior_pdf(sample_book(2), out)
    pages = PdfReader(str(out)).pages
    texts = [p.extract_text() or "" for p in pages]
    opener = next(i for i, t in enumerate(texts) if "Chapter 1" in t[:40])
    assert "Tiny & Brave" not in texts[opener]  # no head on chapter opening
    # body pages: title on right-hand (odd) pages, author on left-hand (even) pages
    recto = [t for i, t in enumerate(texts) if i % 2 == 0 and "Paragraph" in t and "Chapter" not in t[:40]]
    verso = [t for i, t in enumerate(texts) if i % 2 == 1 and "Paragraph" in t]
    assert recto and verso
    assert all("Tiny & Brave" in t for t in recto)
    assert all("A. Writer" in t for t in verso)


def test_bad_trim():
    with pytest.raises(BookError):
        parse_trim("7x7")
