import asyncio

from PIL import Image

from pressready import mcp_server
from test_build import make_manuscript


def test_tools_registered():
    names = {t.name for t in asyncio.run(mcp_server.mcp.list_tools())}
    assert {"build_book", "spine_width", "list_trim_sizes"} <= names


def test_spine_and_trims():
    r = mcp_server.spine_width(100, "cream")
    assert r["ok"] and r["spine_in"] == 0.25
    assert mcp_server.spine_width(100, "x")["ok"] is False
    assert "6x9" in mcp_server.list_trim_sizes()["trim_sizes"]


def test_build_book_ok_and_error(tmp_path):
    ms = tmp_path / "ms"
    make_manuscript(ms)
    art = tmp_path / "front.png"
    Image.new("RGB", (800, 1200), (30, 90, 160)).save(art)
    r = mcp_server.build_book(str(ms), str(art), str(tmp_path / "out"), trim="5x8")
    assert r["ok"] is True
    assert (tmp_path / "out" / "book.epub").is_file()
    bad = mcp_server.build_book(str(ms), str(tmp_path / "nope.png"), str(tmp_path / "o2"))
    assert bad["ok"] is False and "cover" in bad["error"]
