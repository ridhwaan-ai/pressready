"""EPUB 3 writer (stdlib only), shaped for Kindle/KDP upload."""
from __future__ import annotations

import uuid
import zipfile
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from .book import Book, BookError, Section
from .markdown import to_xhtml

CSS = ("body{font-family:serif;line-height:1.5}"
       "h1,h2{text-align:center;margin:2em 0 1.5em;font-weight:normal}"
       "h2{font-size:1.3em;letter-spacing:.05em}"
       "p{margin:0;text-indent:1.3em;text-align:justify}"
       "h1+p,h2+p,h3+p,.scene-break+p{text-indent:0}"
       ".scene-break{text-align:center;text-indent:0;margin:1.2em 0}"
       ".title-page,.copyright-page{text-align:center}"
       ".copyright-page p{text-indent:0;font-size:.85em;margin:.4em 0}"
       "blockquote{margin:1em 2em;font-style:italic}"
       "img.cover{max-width:100%;height:auto}")

_IMAGE_TYPES = {b"\xff\xd8\xff": ("image/jpeg", "jpg"), b"\x89PNG": ("image/png", "png")}


def _image_type(data: bytes) -> tuple[str, str]:
    for magic, kind in _IMAGE_TYPES.items():
        if data.startswith(magic):
            return kind
    raise BookError("cover must be a JPEG or PNG image")


def _page(title: str, inner: str, language: str) -> str:
    return ('<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
            f'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" '
            f'lang="{escape(language)}" xml:lang="{escape(language)}">'
            f'<head><meta charset="utf-8"/><title>{escape(title)}</title>'
            f'<link rel="stylesheet" type="text/css" href="style.css"/></head><body>{inner}</body></html>')


def _body_pages(book: Book) -> list[tuple[str, Section]]:
    """(file name, section) for every content page after the generated pages."""
    pages = []
    for group, sections in (("f", book.front_matter), ("c", book.chapters), ("b", book.back_matter)):
        for i, s in enumerate(sections, 1):
            pages.append((f"{group}{i:03d}.xhtml", s))
    return pages


def build_epub(book: Book, out: str | Path, cover: bytes | None = None, modified: str | None = None) -> dict:
    """Write book to `out` as EPUB 3. `cover` is raw JPEG/PNG bytes. Returns a small summary dict."""
    book.validate()
    out = Path(out)
    modified = modified or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ident = book.identifier or f"urn:uuid:{uuid.uuid4()}"
    full_title = f"{book.title}: {book.subtitle}" if book.subtitle else book.title

    files: dict[str, str] = {}
    title_inner = f'<div class="title-page"><h1>{escape(book.title)}</h1>'
    if book.subtitle:
        title_inner += f"<p><em>{escape(book.subtitle)}</em></p>"
    if book.series:
        title_inner += f"<p>{escape(book.series)}</p>"
    title_inner += f"<p>{escape(book.author)}</p></div>"
    files["titlepage.xhtml"] = _page(full_title, title_inner, book.language)
    year = modified[:4]
    rights = escape(book.rights) if book.rights else f"Copyright &#169; {year} {escape(book.author)}. All rights reserved."
    files["copyright.xhtml"] = _page("Copyright", f'<div class="copyright-page"><p>{rights}</p></div>', book.language)

    pages = _body_pages(book)
    for name, sec in pages:
        inner = f"<h2>{escape(sec.title)}</h2>\n" + to_xhtml(sec.markdown)
        files[name] = _page(sec.title, inner, book.language)

    toc = [(n, s.title) for n, s in pages]
    nav_inner = ('<nav epub:type="toc" id="toc"><h1>Contents</h1><ol>'
                 + "".join(f'<li><a href="{n}">{escape(t)}</a></li>' for n, t in toc) + "</ol></nav>")
    files["nav.xhtml"] = _page("Contents", nav_inner, book.language)

    manifest = ['<item id="css" href="style.css" media-type="text/css"/>',
                '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>']
    spine = []
    cover_name = None
    if cover:
        mime, ext = _image_type(cover)
        cover_name = f"cover.{ext}"
        manifest.append(f'<item id="cover-image" href="{cover_name}" media-type="{mime}" properties="cover-image"/>')
        files["cover.xhtml"] = _page("Cover", f'<div class="title-page"><img class="cover" src="{cover_name}" alt="Cover"/></div>',
                                     book.language)
        manifest.append('<item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>')
        spine.append("cover")
    order = ["titlepage.xhtml", "copyright.xhtml", "nav.xhtml"] + [n for n, _ in pages]
    for n in order:
        iid = n.rsplit(".", 1)[0]
        if n != "nav.xhtml":
            manifest.append(f'<item id="{iid}" href="{n}" media-type="application/xhtml+xml"/>')
        spine.append(iid)

    meta = (f'<dc:identifier id="bid">{escape(ident)}</dc:identifier><dc:title>{escape(full_title)}</dc:title>'
            f'<dc:creator>{escape(book.author)}</dc:creator><dc:language>{escape(book.language)}</dc:language>')
    if book.description:
        meta += f"<dc:description>{escape(book.description)}</dc:description>"
    meta += f'<meta property="dcterms:modified">{modified}</meta>'
    itemrefs = "".join('<itemref idref="%s"/>' % i for i in spine)
    opf = ('<?xml version="1.0" encoding="utf-8"?>\n'
           '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bid">'
           f'<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">{meta}</metadata>'
           f'<manifest>{"".join(manifest)}</manifest>'
           f"<spine>{itemrefs}</spine></package>")

    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip")  # first entry, stored uncompressed
        deflate = zipfile.ZIP_DEFLATED
        z.writestr("META-INF/container.xml",
                   '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                   '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>'
                   "</rootfiles></container>", compress_type=deflate)
        z.writestr("OEBPS/content.opf", opf, compress_type=deflate)
        z.writestr("OEBPS/style.css", CSS, compress_type=deflate)
        if cover:
            z.writestr(f"OEBPS/{cover_name}", cover)
        for name, content in files.items():
            z.writestr(f"OEBPS/{name}", content, compress_type=deflate)
    return {"path": str(out), "chapters": len(book.chapters), "pages": len(files)}
