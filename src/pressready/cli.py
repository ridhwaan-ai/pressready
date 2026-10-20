"""Command line interface: `pressready build manuscript/ --cover front.png --trim 5.5x8.5 --paper cream`."""
from __future__ import annotations

import argparse
import json
import sys

from .book import BookError
from .build import build


def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pressready", description="Manuscript in, publish-ready book out.")
    sub = p.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="build EPUB, interior PDF, wrap cover and checklist.json")
    b.add_argument("manuscript", help="folder with book.json and Markdown chapters")
    b.add_argument("--cover", required=True, help="front cover image (PNG/JPG)")
    b.add_argument("--out", default="out", help="output directory (default: out)")
    b.add_argument("--trim", default="5.5x8.5", help="5x8, 5.5x8.5, 6x9 or 8.5x11")
    b.add_argument("--paper", default="white", choices=["white", "cream"])
    b.add_argument("--keyword", action="append", default=[], help="KDP keyword (repeatable)")
    b.add_argument("--back-text", default="", help="back cover blurb (default: book description)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    try:
        checklist = build(args.manuscript, args.cover, args.out, trim=args.trim, paper=args.paper,
                          keywords=args.keyword or None, back_text=args.back_text)
    except (BookError, ValueError) as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        return 1
    print(json.dumps(checklist, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
