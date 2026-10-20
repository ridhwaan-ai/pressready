"""Full-wrap paperback cover PDF for KDP (ReportLab + Pillow).

Geometry (see reference/LESSONS.md):
- width  = bleed + back trim + spine + front trim + bleed, height = trim height + 2 * bleed (bleed = 0.125 in)
- spine width comes from page count and paper type
- spine text only above 79 pages, kept 0.0625 in clear of each spine edge
- KDP prints a barcode box bottom-right of the back cover: kept clear of our text
"""
from __future__ import annotations

from html import escape
from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

from . import spine_width_in
from .book import Book, BookError
from .pdf import _FONT, _register_fonts, parse_trim

BLEED_IN = 0.125
SPINE_TEXT_MIN_PAGES = 79
SPINE_TEXT_CLEAR_IN = 0.0625
SAFE_IN = 0.25  # keep text this far inside the trim edge
BARCODE_W_IN, BARCODE_H_IN = 2.0, 1.2  # KDP barcode box, bottom-right of back cover


def wrap_dimensions(trim: str, pages: int, paper: str = "white") -> dict:
    """Exact wrap geometry in inches."""
    if paper not in ("white", "cream"):
        raise BookError(f"unsupported paper '{paper}': use 'white' or 'cream'")
    if pages < 24:
        raise BookError(f"page count {pages} is below the KDP paperback minimum of 24")
    tw, th = parse_trim(trim)
    spine = spine_width_in(pages, paper)
    return {
        "trim_w": tw, "trim_h": th, "spine": spine, "bleed": BLEED_IN,
        "width": round(2 * BLEED_IN + 2 * tw + spine, 4),
        "height": round(th + 2 * BLEED_IN, 4),
        "spine_text_allowed": pages > SPINE_TEXT_MIN_PAGES,
    }


def _check_image(path: Path):
    from PIL import Image, UnidentifiedImageError
    try:
        with Image.open(path) as im:
            im.load()
            return im.size
    except (OSError, UnidentifiedImageError) as e:
        raise BookError(f"front cover image '{path}' cannot be read as an image: {e}") from e


def build_wrap_cover(book: Book, front_image: str | Path, out_path: str | Path, pages: int,
                     trim: str = "5.5x8.5", paper: str = "white", back_text: str = "",
                     background: str = "#1f2a44") -> dict:
    """Write the wrap cover PDF and return its geometry (inches)."""
    book.validate()
    front_image = Path(front_image)
    if not front_image.is_file():
        raise BookError(f"front cover image not found: {front_image}")
    iw, ih = _check_image(front_image)
    d = wrap_dimensions(trim, pages, paper)
    try:
        bg = HexColor(background)
    except Exception:
        raise BookError(f"background '{background}' is not a hex colour like #1f2a44") from None
    _register_fonts()

    W, H = d["width"] * inch, d["height"] * inch
    b, tw, th, sp = d["bleed"] * inch, d["trim_w"] * inch, d["trim_h"] * inch, d["spine"] * inch
    front_x = b + tw + sp  # left edge of the front trim area

    c = canvas.Canvas(str(out_path), pagesize=(W, H))
    c.setTitle(f"{book.title} (cover)")
    c.setAuthor(book.author)
    c.setCreator("PressReady")
    c.setFillColor(bg)
    c.rect(0, 0, W, H, stroke=0, fill=1)

    # front image: cover-fit into front panel including top/bottom/right bleed, cropped by a clip
    px, py, pw, ph = front_x, 0, tw + b, H
    scale = max(pw / iw, ph / ih)
    dw, dh = iw * scale, ih * scale
    c.saveState()
    p = c.beginPath()
    p.rect(px, py, pw, ph)
    c.clipPath(p, stroke=0, fill=0)
    c.drawImage(str(front_image), px + (pw - dw) / 2, py + (ph - dh) / 2, dw, dh, mask="auto")
    c.restoreState()

    # back cover text, clear of the barcode box
    if back_text.strip():
        style = ParagraphStyle("back", fontName=_FONT, fontSize=11, leading=15, textColor=white, alignment=TA_CENTER)
        safe = SAFE_IN * inch
        bx, bw = b + safe, tw - 2 * safe
        top = H - b - safe
        para = Paragraph(escape(back_text.strip(), quote=False).replace("\n", "<br/>"), style)
        _, h = para.wrap(bw, top)
        para.drawOn(c, bx, top - h)

    # spine text
    if d["spine_text_allowed"]:
        avail = sp - 2 * SPINE_TEXT_CLEAR_IN * inch
        size = min(14.0, avail * 0.7)
        if size >= 6:
            c.saveState()
            c.setFillColor(white)
            c.setFont(_FONT + "-Bold", size)
            c.translate(b + tw + sp / 2, H / 2)
            c.rotate(-90)  # reads top to bottom
            c.drawCentredString(0, -size * 0.35, f"{book.title}  |  {book.author}"[:90])
            c.restoreState()
            d["spine_text_drawn"] = True
    d.setdefault("spine_text_drawn", False)

    # barcode box is reserved (not drawn): document its position for callers
    d["barcode_box_in"] = {
        "x": round(d["bleed"] + d["trim_w"] - SAFE_IN - BARCODE_W_IN, 4),
        "y": round(d["bleed"] + SAFE_IN, 4), "w": BARCODE_W_IN, "h": BARCODE_H_IN}
    d["front_image_px"] = [iw, ih]
    c.showPage()
    c.save()
    return d
