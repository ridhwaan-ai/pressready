from pressready.book import Book, Section
from pressready.checklist import manuscript_warnings


def _book(*chapters):
    return Book(title="T", author="A", chapters=[Section(t, m) for t, m in chapters])


def test_clean_book_has_no_warnings():
    assert manuscript_warnings(_book(("One", "Hello world."), ("Two", "More."))) == []


def test_empty_and_duplicate():
    w = manuscript_warnings(_book(("One", "  "), ("one", "Text.")))
    assert any("is empty" in x for x in w) and any("duplicate" in x for x in w)


def test_unsupported_markdown_and_placeholders():
    w = manuscript_warnings(_book(("One", "![alt](x.png)\n\n| a | b |\n\nTODO fix this")))
    assert any("image" in x for x in w)
    assert any("table" in x for x in w)
    assert any("placeholder" in x for x in w)
