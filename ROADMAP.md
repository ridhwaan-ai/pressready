# PressReady roadmap

- [ ] M1 Core library: Markdown chapters -> EPUB + interior PDF + wrap cover PDF (tests, CI green)
  - [x] Book model + folder loader (book.py)
  - [x] Minimal Markdown -> XHTML (markdown.py)
  - [x] EPUB 3 writer (epub.py) + structure tests (awaiting first CI result)
  - [ ] Interior PDF at trim sizes (pdf.py, ReportLab, embedded Vera fonts; written + tests, awaiting CI)
    - todo: custom font option, running heads, print TOC, non-Latin glyph coverage
  - [ ] Wrap cover PDF (cover.py + tests written, awaiting CI; todo: barcode-box guide option, back-cover styling)
  - [x] Upload checklist JSON (checklist.py: title warnings, AI disclosure; awaiting CI)
  - [x] build() orchestrator (build.py) + end-to-end test (tests/test_build.py; awaiting CI)
- [ ] M2 CLI + MCP server
  - [x] CLI `pressready build` (cli.py + tests/test_cli.py; awaiting CI)
  - [x] MCP server (mcp_server.py, FastMCP: build_book, spine_width, list_trim_sizes; tests/test_mcp.py; awaiting CI)
- [ ] M3 HTTP API + OpenAPI + agent docs (llms.txt, quickstart)
  - [x] api.py: POST/GET /v1/books, file downloads, typed errors, /llms.txt, /quickstart.txt (in-memory 15-min jobs; tests/test_api.py; awaiting CI)
  - [ ] todo: machine-readable pricing/limits endpoint, request size limit, README agent docs
- [ ] M4 Deploy + self-serve keys + pricing (needs Owner)
- [ ] M5 First agent customers
