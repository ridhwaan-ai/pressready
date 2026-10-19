# PressReady roadmap

- [ ] M1 Core library: Markdown chapters -> EPUB + interior PDF + wrap cover PDF (tests, CI green)
  - [x] Book model + folder loader (book.py)
  - [x] Minimal Markdown -> XHTML (markdown.py)
  - [x] EPUB 3 writer (epub.py) + structure tests (awaiting first CI result)
  - [ ] Interior PDF at trim sizes (pdf.py, ReportLab, embedded Vera fonts; written + tests, awaiting CI)
    - todo: custom font option, running heads, print TOC, non-Latin glyph coverage
  - [ ] Wrap cover PDF (spine from page count, exact MediaBox)
  - [ ] Upload checklist JSON (title warnings, AI disclosure)
  - [ ] End-to-end sample-book test
- [ ] M2 CLI + MCP server
- [ ] M3 HTTP API + OpenAPI + agent docs (llms.txt, quickstart)
- [ ] M4 Deploy + self-serve keys + pricing (needs Owner)
- [ ] M5 First agent customers
