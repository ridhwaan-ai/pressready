"""MCP server exposing PressReady to agents. Run with `pressready-mcp` (stdio)."""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import spine_width_in
from .book import BookError
from .build import build
from .pdf import TRIM_SIZES

mcp = FastMCP("pressready")


@mcp.tool()
def build_book(manuscript_dir: str, cover_image: str, out_dir: str = "out", trim: str = "5.5x8.5",
               paper: str = "white", keywords: list[str] | None = None, back_text: str = "") -> dict:
    """Build a Kindle EPUB, print interior PDF, full-wrap cover PDF and KDP upload checklist.

    manuscript_dir: folder containing book.json and Markdown chapters.
    cover_image: path to the front cover image (PNG/JPG).
    trim: one of 5x8, 5.5x8.5, 6x9, 8.5x11. paper: white or cream.
    Returns {"ok": true, ...checklist} or {"ok": false, "error": "what to fix"}.
    """
    try:
        return build(manuscript_dir, cover_image, out_dir, trim=trim, paper=paper,
                     keywords=keywords, back_text=back_text)
    except (BookError, ValueError) as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def spine_width(pages: int, paper: str = "white") -> dict:
    """Compute KDP paperback spine width in inches for a page count and paper type (white or cream)."""
    if paper not in ("white", "cream"):
        return {"ok": False, "error": "paper must be 'white' or 'cream'"}
    if pages < 1:
        return {"ok": False, "error": "pages must be >= 1"}
    return {"ok": True, "pages": pages, "paper": paper, "spine_in": spine_width_in(pages, paper)}


@mcp.tool()
def list_trim_sizes() -> dict:
    """List supported print trim sizes (inches)."""
    return {"ok": True, "trim_sizes": {k: list(v) for k, v in TRIM_SIZES.items()}}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
