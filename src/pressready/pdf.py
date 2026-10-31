"""Print interior PDF for KDP paperbacks (ReportLab, fonts embedded).

Rules baked in (see reference/LESSONS.md and KDP print guidelines):
- exact trim page size, mirrored margins with a gutter safe up to ~800 pages
- chapters start on a right-hand (odd) page; the skipped left page is blank and unnumbered
- page count is padded to an even number, at least 24 pages
- fonts are embedded (KDP rejects unembedded fonts): the bundled Crimson Text serif (OFL)
"""
from __future__ import annotations

import io
import os
import re
from pathlib import Path

import reportlab
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, ListFlowable, ListItem, PageBreak,
                                PageTemplate, Paragraph, Spacer)

from .book import Book, BookError, Section
from .markdown import to_xhtml

TRIM_SIZES = {
    "5x8": (5.0, 8.0),
    "5.5x8.5": (5.5, 8.5),
    "6x9": (6.0, 9.0),
    "8.5x11": (8.5, 11.0),
}
MIN_PAGES = 24
INNER_MARGIN_IN = 0.75  # KDP minimum gutter is 0.375-0.875 depending on page count; 0.75 covers up to 700 pages
OUTER_MARGIN_IN = 0.5
TOP_MARGIN_IN = 0.75
BOTTOM_MARGIN_IN = 0.75

_FONT = "PRSerif"
_fonts_ready = False


def parse_trim(trim: str) -> tuple[float, float]:
    try:
        return TRIM_SIZES[trim.lower().replace(" ", "")]
    except KeyError:
        raise BookError(f"unsupported trim size '{trim}': use one of {', '.join(TRIM_SIZES)}") from None


def _register_fonts() -> None:
    global _fonts_ready
    if _fonts_ready:
        return
    # Crimson Text (SIL Open Font License, see fonts/OFL.txt): a book serif we may embed and redistribute
    d = Path(__file__).parent / "fonts"
    for suffix, file in (("", "CrimsonText-Regular.ttf"), ("-Bold", "CrimsonText-Bold.ttf"),
                         ("-Italic", "CrimsonText-Italic.ttf"), ("-BoldItalic", "CrimsonText-BoldItalic.ttf")):
        pdfmetrics.registerFont(TTFont(_FONT + suffix, str(d / file)))
    pdfmetrics.registerFontFamily(_FONT, normal=_FONT, bold=_FONT + "-Bold", italic=_FONT + "-Italic",
                                  boldItalic=_FONT + "-BoldItalic")
    # ReportLab otherwise declares Helvetica (not embedded) on every page, which KDP's checker can flag
    from reportlab import rl_config
    rl_config.canvas_basefontname = _FONT
    _fonts_ready = True


class _Mark(Flowable):
    """Zero-size marker: the page it lands on gets no page number."""

    def wrap(self, aw, ah):
        return 0, 0

    def draw(self):
        self.canv._pr_no_number = True


class _NoHead(Flowable):
    """Zero-size marker: the page it lands on gets no running head (chapter opening pages)."""

    def wrap(self, aw, ah):
        return 0, 0

    def draw(self):
        self.canv._pr_no_head = True


class _FillIfVerso(Flowable):
    """Fills the rest of an even (left-hand) page so the next flowable starts on an odd page."""

    def wrap(self, aw, ah):
        self._fill = self.canv.getPageNumber() % 2 == 0
        return (aw, max(ah - 1, 0)) if self._fill else (0, 0)

    def draw(self):
        if self._fill:
            self.canv._pr_no_number = True


class _BlankPage(Flowable):
    def wrap(self, aw, ah):
        return aw, max(ah - 1, 0)

    def draw(self):
        self.canv._pr_no_number = True


class _Doc(BaseDocTemplate):
    def afterPage(self):
        # page numbers are 1-based and page 1 is a right-hand page
        self.handle_nextPageTemplate("verso" if (self.page + 1) % 2 == 0 else "recto")


def _styles(font_size: float) -> dict[str, ParagraphStyle]:
    lead = round(font_size * 1.35, 1)
    body = ParagraphStyle("body", fontName=_FONT, fontSize=font_size, leading=lead, alignment=TA_JUSTIFY,
                          firstLineIndent=0.25 * inch)
    return {
        "body": body,
        "first": ParagraphStyle("first", parent=body, firstLineIndent=0),
        "quote": ParagraphStyle("quote", parent=body, leftIndent=0.35 * inch, rightIndent=0.35 * inch,
                                firstLineIndent=0, fontName=_FONT + "-Italic", spaceBefore=4, spaceAfter=6),
        "scene": ParagraphStyle("scene", parent=body, alignment=TA_CENTER, firstLineIndent=0,
                                spaceBefore=lead * 0.6, spaceAfter=lead * 0.6),
        "h1": ParagraphStyle("h1", fontName=_FONT + "-Bold", fontSize=font_size * 1.9, leading=font_size * 2.3,
                             alignment=TA_CENTER, spaceBefore=0.9 * inch, spaceAfter=0.5 * inch),
        "h2": ParagraphStyle("h2", fontName=_FONT + "-Bold", fontSize=font_size * 1.3, leading=font_size * 1.7,
                             spaceBefore=lead, spaceAfter=lead * 0.5, keepWithNext=True),
        "title": ParagraphStyle("title", fontName=_FONT + "-Bold", fontSize=30, leading=36,
                                alignment=TA_CENTER, spaceAfter=14),
        "subtitle": ParagraphStyle("subtitle", fontName=_FONT, fontSize=15, leading=20, alignment=TA_CENTER,
                                   spaceAfter=14),
        "author": ParagraphStyle("author", fontName=_FONT, fontSize=14, leading=18, alignment=TA_CENTER),
        "small": ParagraphStyle("small", fontName=_FONT, fontSize=9, leading=12, alignment=TA_CENTER,
                                spaceAfter=6),
    }


def _fix_tags(x: str) -> str:
    x = x.replace("<strong>", "<b>").replace("</strong>", "</b>")
    return x.replace("<em>", "<i>").replace("</em>", "</i>")


def _section_flowables(sec: Section, st: dict[str, ParagraphStyle], heading: bool = True) -> list:
    from html import escape
    out: list = [PageBreak(), _FillIfVerso()]
    if heading:
        out.append(Paragraph(escape(sec.title, quote=False), st["h1"]))
        out.append(_NoHead())
    after_break = True
    for line in to_xhtml(sec.markdown).split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith('<p class="scene-break">'):
            out.append(Paragraph("*&nbsp;&nbsp;&nbsp;*&nbsp;&nbsp;&nbsp;*", st["scene"]))
            after_break = True
        elif (m := re.match(r"<h([1-6])>(.*)</h\1>$", line)):
            out.append(Paragraph(_fix_tags(m.group(2)), st["h2"]))
            after_break = True
        elif (m := re.match(r"<blockquote><p>(.*)</p></blockquote>$", line)):
            out.append(Paragraph(_fix_tags(m.group(1)), st["quote"]))
            after_break = True
        elif (m := re.match(r"<(ul|ol)>(.*)</\1>$", line)):
            items = [ListItem(Paragraph(_fix_tags(i), st["first"])) for i in re.findall(r"<li>(.*?)</li>", m.group(2))]
            out.append(ListFlowable(items, bulletType="bullet" if m.group(1) == "ul" else "1",
                                    bulletFontName=_FONT))
            after_break = True
        elif (m := re.match(r"<p>(.*)</p>$", line)):
            out.append(Paragraph(_fix_tags(m.group(1)), st["first"] if after_break else st["body"]))
            after_break = False
    return out


def _story(book: Book, st: dict[str, ParagraphStyle], pad_pages: int) -> list:
    from html import escape
    if book.own_front_matter:
        # the manuscript supplies its own title/copyright pages: start directly with its first section
        story: list = [_Mark()]
    else:
        story = [_Mark(), Spacer(1, 1.6 * inch), Paragraph(escape(book.title, quote=False), st["title"])]
        if book.subtitle:
            story.append(Paragraph(escape(book.subtitle, quote=False), st["subtitle"]))
        story += [Spacer(1, 0.6 * inch), Paragraph(escape(book.author, quote=False), st["author"])]
        # copyright page (unnumbered)
        story += [PageBreak(), _Mark(), Spacer(1, 4.0 * inch)]
        story.append(Paragraph(escape(book.rights or f"Copyright © {book.author}. All rights reserved.",
                                      quote=False), st["small"]))
    body: list = []
    for sec in book.front_matter + book.chapters + book.back_matter:
        body += _section_flowables(sec, st)
    if book.own_front_matter and body:
        body = body[1:]  # drop the leading PageBreak so page 1 is not blank
    story += body
    for _ in range(pad_pages):
        story += [PageBreak(), _BlankPage()]
    return story


def _render(book: Book, trim: tuple[float, float], font_size: float, pad_pages: int) -> tuple[bytes, int]:
    _register_fonts()
    w, h = trim[0] * inch, trim[1] * inch
    st = _styles(font_size)
    buf = io.BytesIO()
    doc = _Doc(buf, pagesize=(w, h), title=book.title, author=book.author, creator="PressReady",
               leftMargin=0, rightMargin=0, topMargin=0, bottomMargin=0)

    seen = [0]

    def footer(canv, _doc):
        seen[0] = max(seen[0], canv.getPageNumber())
        no_head = getattr(canv, "_pr_no_head", False)
        canv._pr_no_head = False
        if getattr(canv, "_pr_no_number", False):
            canv._pr_no_number = False
            return
        if not no_head:
            # running head: author on left-hand pages, title on right-hand pages
            canv.setFont(_FONT + "-Italic", 9)
            canv.drawCentredString(w / 2, h - 0.5 * inch, book.author if canv.getPageNumber() % 2 == 0 else book.title)
        canv.setFont(_FONT, 9)
        canv.drawCentredString(w / 2, 0.4 * inch, str(canv.getPageNumber()))

    def frame(name: str, left_in: float, right_in: float) -> Frame:
        return Frame(left_in * inch, BOTTOM_MARGIN_IN * inch, w - (left_in + right_in) * inch,
                     h - (TOP_MARGIN_IN + BOTTOM_MARGIN_IN) * inch, id=name,
                     leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    doc.addPageTemplates([
        PageTemplate("recto", [frame("r", INNER_MARGIN_IN, OUTER_MARGIN_IN)], onPageEnd=footer),
        PageTemplate("verso", [frame("v", OUTER_MARGIN_IN, INNER_MARGIN_IN)], onPageEnd=footer),
    ])
    doc.build(_story(book, st, pad_pages))
    return buf.getvalue(), seen[0]


def build_interior_pdf(book: Book, out_path: str | Path, trim: str = "5.5x8.5", font_size: float = 10.5) -> int:
    """Write the interior PDF and return its page count (even, >= 24)."""
    book.validate()
    size = parse_trim(trim)
    data, pages = _render(book, size, font_size, 0)
    target = max(MIN_PAGES, pages + pages % 2)
    if target != pages:
        data, pages = _render(book, size, font_size, target - pages)
    Path(out_path).write_bytes(data)
    return pages
