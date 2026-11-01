import json

from pressready.api import BookIn
from pressready.book import Book


def test_from_dir_print_toc(tmp_path):
    (tmp_path / "01.md").write_text("# One\n\nText.")
    (tmp_path / "book.json").write_text(json.dumps({"title": "T", "author": "A"}))
    assert Book.from_dir(tmp_path).print_toc is False
    (tmp_path / "book.json").write_text(json.dumps({"title": "T", "author": "A", "print_toc": True}))
    assert Book.from_dir(tmp_path).print_toc is True


def test_api_model_has_print_toc():
    assert BookIn.model_fields["print_toc"].default is False
