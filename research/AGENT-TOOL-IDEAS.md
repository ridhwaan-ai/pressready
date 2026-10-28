# Agent tool ideas (ranked, partly evidenced)

Do not start a second product without the Owner's OK. Updated 2026-10-28.

| # | Idea | Why agents struggle | Evidence |
|---|------|--------------------|----------|
| 1 | Cover-image sanity checker (size, ratio, format vs KDP rules) | Rules live in human help pages; a bad cover is rejected at upload | KDP help: ideal 2560x1600 px, min 1000x625, max 10,000 px, JPEG/TIFF, under 50 MB, ratio about 1.6:1 (https://kdp.amazon.com/en_US/help/topic/G200645690). Fits PressReady directly: cheap add-on to the existing checklist. |
| 2 | Document conversion for publishing (DOCX -> clean Markdown) | Authors hold Word files | Crowded: Microsoft MarkItDown (about 90k GitHub stars, 29+ formats, 300+ open issues), IBM Docling MCP, 15+ PDF/DOCX MCP servers (https://dev.to/grove_chatforest/pdf-document-processing-mcp-servers-markitdown-docling-pdf-reader-more-66f). Do not build; link to them instead. |
| 3 | Invoice/receipt PDF extraction to JSON | Human-formatted PDFs | Same crowded PDF-extraction MCP category as #2. Low priority. |
| 4 | Form-field schema extractor for web forms | Forms built for humans | Crowded; ToS risk. Low priority. |

Takeaway: generic document conversion is saturated. The niche, publishing-specific gaps (KDP-rule validators) are where PressReady has an edge.

Suggested next step (needs no new product): add a cover-image validator to PressReady's checklist using the KDP numbers above.
