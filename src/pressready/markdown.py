"""Tiny Markdown -> XHTML converter for manuscripts (no dependencies).

Supports: # headings, paragraphs, *em*/_em_, **strong**, > quotes, - / 1. lists,
scene breaks (---, ***, * * *). Everything else is escaped text.
"""
import html
import re

_SCENE = re.compile(r"^(\*\s*\*\s*\*[\s*]*|-{3,}|_{3,})$")
_UL = re.compile(r"^[-*+]\s+(.*)$")
_OL = re.compile(r"^\d+[.)]\s+(.*)$")


def inline(text: str) -> str:
    t = html.escape(text, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", t)
    t = re.sub(r"(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)", r"<em>\1</em>", t)
    return t


def to_xhtml(md: str, drop_first_h1: bool = True) -> str:
    """Convert Markdown to an XHTML fragment. The first '# ' heading is dropped (it is the section title)."""
    blocks = re.split(r"\n\s*\n", md.replace("\r\n", "\n").strip())
    out = []
    dropped = not drop_first_h1
    for block in blocks:
        lines = [ln.rstrip() for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        first = lines[0].strip()
        if len(lines) == 1 and _SCENE.match(first):
            out.append('<p class="scene-break">&#10086;</p>')
            continue
        h = re.match(r"^(#{1,6})\s+(.*?)\s*#*$", first)
        if h and len(lines) == 1:
            level = len(h.group(1))
            if level == 1 and not dropped:
                dropped = True
                continue
            out.append(f"<h{level}>{inline(h.group(2))}</h{level}>")
            continue
        if all(ln.lstrip().startswith(">") for ln in lines):
            inner = " ".join(ln.lstrip()[1:].strip() for ln in lines)
            out.append(f"<blockquote><p>{inline(inner)}</p></blockquote>")
            continue
        for rx, tag in ((_UL, "ul"), (_OL, "ol")):
            if all(rx.match(ln.strip()) for ln in lines):
                items = "".join(f"<li>{inline(rx.match(ln.strip()).group(1))}</li>" for ln in lines)
                out.append(f"<{tag}>{items}</{tag}>")
                break
        else:
            out.append(f"<p>{inline(' '.join(ln.strip() for ln in lines))}</p>")
    return "\n".join(out)
