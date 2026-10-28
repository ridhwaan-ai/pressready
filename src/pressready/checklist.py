"""Machine-readable KDP upload checklist."""
from __future__ import annotations

import re

from .book import Book

MAX_TITLE = 200
MAX_DESCRIPTION = 4000
MAX_KEYWORDS = 7
MAX_KEYWORD_CHARS = 50
_RISKY_TITLE_WORDS = {
    "free": "KDP rejects titles that promise 'free' content",
    "bestseller": "KDP rejects unverifiable claims such as 'bestseller'",
    "best seller": "KDP rejects unverifiable claims such as 'best seller'",
    "best-selling": "KDP rejects unverifiable claims such as 'best-selling'",
    "#1": "KDP rejects unverifiable rank claims such as '#1'",
    "kindle": "'Kindle' is an Amazon trademark; KDP rejects it in titles",
    "amazon": "'Amazon' is a trademark; KDP rejects it in titles",
}


def title_warnings(title: str, subtitle: str = "") -> list[str]:
    text = f"{title} {subtitle}".lower()
    out = []
    for word, why in _RISKY_TITLE_WORDS.items():
        if re.search(r"(?<![\w])" + re.escape(word) + r"(?![\w])", text) or (word == "#1" and "#1" in text):
            out.append(f"title contains '{word}': {why}")
    return out


MAX_COVER_BYTES = 50 * 1024 * 1024


def cover_image_report(path) -> dict:
    """Check a front-cover image against KDP's Kindle cover rules; returns facts plus warnings."""
    from pathlib import Path

    from PIL import Image

    p = Path(path)
    warnings: list[str] = []
    size = p.stat().st_size
    with Image.open(p) as im:
        fmt, (w, h) = im.format, im.size
    if fmt not in ("JPEG", "TIFF", "PNG"):
        warnings.append(f"cover format is {fmt}; use JPEG, TIFF or PNG")
    if min(w, h) < 625 or max(w, h) < 1000:
        warnings.append(f"cover is {w}x{h}px; KDP needs at least 1000px on the longest side "
                        "(2560x1600 recommended)")
    elif max(w, h) > 10000:
        warnings.append(f"cover is {w}x{h}px; KDP allows at most 10000px per side")
    if w >= h:
        warnings.append("cover is not portrait; a front cover should be taller than wide (ratio 1.6)")
    elif abs(h / w - 1.6) > 0.15:
        warnings.append(f"cover ratio is {h / w:.2f}; KDP recommends height/width of 1.6")
    if size > MAX_COVER_BYTES:
        warnings.append("cover file exceeds 50 MB")
    return {"format": fmt, "width_px": w, "height_px": h, "ratio": round(h / w, 3),
            "bytes": size, "warnings": warnings}


def build_checklist(book: Book, *, pages: int, trim: str, paper: str, spine_in: float,
                    wrap_size_in: tuple[float, float], keywords: list[str] | None = None,
                    ai_generated_text: bool = True, ai_generated_images: bool = False,
                    files: dict[str, str] | None = None, cover_report: dict | None = None) -> dict:
    """Every value the KDP paperback/Kindle forms ask for, plus warnings an agent should fix."""
    keywords = [k.strip() for k in (keywords or []) if k.strip()]
    warnings = title_warnings(book.title, book.subtitle)
    if cover_report:
        warnings += [f"front cover: {w}" for w in cover_report["warnings"]]
    if len(book.title) + len(book.subtitle) > MAX_TITLE:
        warnings.append(f"title + subtitle exceed {MAX_TITLE} characters")
    if not book.description.strip():
        warnings.append("description is empty: add one (max 4000 characters)")
    elif len(book.description) > MAX_DESCRIPTION:
        warnings.append(f"description is {len(book.description)} characters; KDP allows {MAX_DESCRIPTION}")
    if len(keywords) > MAX_KEYWORDS:
        warnings.append(f"{len(keywords)} keywords given; KDP accepts {MAX_KEYWORDS}")
    for k in keywords:
        if len(k) > MAX_KEYWORD_CHARS:
            warnings.append(f"keyword '{k[:20]}...' exceeds {MAX_KEYWORD_CHARS} characters")
    if pages < 24:
        warnings.append("paperback needs at least 24 pages")
    return {
        "book_details": {
            "language": book.language,
            "title": book.title,
            "subtitle": book.subtitle,
            "series": book.series,
            "author": book.author,
            "description": book.description,
            "keywords": keywords[:MAX_KEYWORDS],
        },
        "content": {
            "publishing_rights": "I own the copyright and I hold necessary publishing rights",
            "ai_content_disclosure": {
                "text_ai_generated": ai_generated_text,
                "images_ai_generated": ai_generated_images,
                "note": "KDP asks you to declare AI-generated content; answer truthfully in the KDP form.",
            },
            "isbn": "Use KDP's free ISBN or your own; PressReady does not assign one.",
        },
        "paperback": {
            "trim_size": trim,
            "paper": paper,
            "bleed": "bleed (cover has bleed; interior has none)",
            "page_count": pages,
            "spine_width_in": spine_in,
            "cover_wrap_size_in": {"width": wrap_size_in[0], "height": wrap_size_in[1]},
        },
        "front_cover_image": {k: v for k, v in (cover_report or {}).items() if k != "warnings"},
        "files": files or {},
        "warnings": warnings,
        "ok": not warnings,
    }
