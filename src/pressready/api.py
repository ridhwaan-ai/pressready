"""HTTP API (FastAPI). Jobs are held in memory and expire quickly (free hosting has no disk)."""
from __future__ import annotations

import base64
import binascii
import tempfile
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from . import access, spine_width_in
from .book import Book, BookError, Section
from .build import build
from .pdf import TRIM_SIZES

JOB_TTL_SECONDS = 15 * 60
MAX_JOBS = 50
MAX_BODY_BYTES = 15 * 1024 * 1024
LIMITS = {"max_request_bytes": MAX_BODY_BYTES, "job_ttl_seconds": JOB_TTL_SECONDS,
          "max_active_jobs": MAX_JOBS, "trim_sizes": ["5x8", "5.5x8.5", "6x9", "8.5x11"],
          "paper": ["white", "cream"]}
# Placeholder until the Owner approves real pricing (M4).
PRICING = {"currency": "USD", "status": "free_beta", "plans": [
    {"name": "free_beta", "price_usd": 0, "builds_per_month": None,
     "notes": "No API key needed during beta. Paid plans will be announced here."}]}
FILES = {"book.epub": "application/epub+zip", "interior.pdf": "application/pdf",
         "cover-wrap.pdf": "application/pdf", "checklist.json": "application/json"}

LLMS_TXT = """# PressReady
> Manuscript in, publish-ready book out. Send Markdown chapters, metadata and a front cover image;
> get a Kindle EPUB, a print interior PDF, a full-wrap paperback cover PDF and a KDP upload checklist (JSON).

## API
- POST /v1/books : create a build job (JSON body, see /openapi.json). Returns job id and status.
- GET /v1/books/{id} : status, checklist and download URLs (files expire after 15 minutes).
- GET /v1/books/{id}/files/{name} : download book.epub, interior.pdf, cover-wrap.pdf, checklist.json.
- GET /v1/spine?pages=200&paper=cream : spine width in inches.
- GET /v1/trim-sizes : supported trim sizes.
- GET /v1/limits : request size, job lifetime, allowed values (JSON).
- GET /v1/pricing : machine-readable pricing (JSON). Free tier: a few builds per day, no key.
  Unlimited: send a license key as 'Authorization: Bearer <key>' (see buy_url in /v1/pricing).
- Errors: {"error": {"code": "...", "message": "what to fix"}}.

## Docs
- OpenAPI: /openapi.json
- Quickstart: /quickstart.txt
"""

QUICKSTART = """PressReady quickstart (3 calls)
1. Create the job. cover_image_base64 is a PNG/JPG front cover, base64 encoded.
   curl -X POST $HOST/v1/books -H 'content-type: application/json' -d '{
     "title": "My Book", "author": "A. Writer", "trim": "5.5x8.5", "paper": "cream",
     "chapters": [{"title": "One", "markdown": "# One\\n\\nHello."}],
     "cover_image_base64": "<base64>"}'
   -> {"id": "...", "status": "done", "checklist": {...}, "files": {"book.epub": "/v1/books/<id>/files/book.epub", ...}}
2. GET /v1/books/<id> to re-read status and URLs.
3. Download each file from its URL, then upload to KDP by hand (KDP has no upload API).
Errors are typed: {"error": {"code": "invalid_book", "message": "..."}} with HTTP 422.
"""


class SectionIn(BaseModel):
    title: str = ""
    markdown: str


class BookIn(BaseModel):
    title: str
    author: str
    subtitle: str = ""
    series: str = ""
    language: str = "en"
    description: str = ""
    rights: str = ""
    identifier: str = ""
    own_front_matter: bool = False  # true: front_matter holds your own title/copyright pages; we add none
    chapters: list[SectionIn] = Field(min_length=1)
    front_matter: list[SectionIn] = []
    back_matter: list[SectionIn] = []
    cover_image_base64: str
    trim: str = "5.5x8.5"
    paper: str = "white"
    keywords: list[str] | None = None
    back_text: str = ""


app = FastAPI(title="PressReady", version="0.1.0",
              description="Manuscript in, publish-ready book out (EPUB, interior PDF, wrap cover, KDP checklist).")
_jobs: dict[str, dict] = {}


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def _sweep() -> None:
    now = time.time()
    for jid in [j for j, v in _jobs.items() if now - v["created"] > JOB_TTL_SECONDS]:
        _jobs.pop(jid)["tmp"].cleanup()


def _sections(items: list[SectionIn]) -> list[Section]:
    out = []
    for i, s in enumerate(items, 1):
        title = s.title.strip()
        if not title:
            for line in s.markdown.splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
        out.append(Section(title or f"Section {i}", s.markdown))
    return out


def _client(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown")


@app.post("/v1/books", status_code=201)
def create_book(req: BookIn, request: Request):
    _sweep()
    auth = request.headers.get("authorization", "")
    key = auth[7:].strip() if auth.lower().startswith("bearer ") else None
    allowed, code, message = access.check(key, _client(request))
    if not allowed:
        return _error(402 if code == "free_limit" else 401, code, message)
    if len(_jobs) >= MAX_JOBS:
        return _error(503, "busy", "too many active jobs; retry in a few minutes")
    if req.trim not in TRIM_SIZES:
        return _error(422, "invalid_trim", f"trim must be one of {sorted(TRIM_SIZES)}")
    if req.paper not in ("white", "cream"):
        return _error(422, "invalid_paper", "paper must be 'white' or 'cream'")
    try:
        cover = base64.b64decode(req.cover_image_base64, validate=True)
    except (binascii.Error, ValueError):
        return _error(422, "invalid_cover", "cover_image_base64 is not valid base64")
    tmp = tempfile.TemporaryDirectory(prefix="pressready-")
    root = Path(tmp.name)
    try:
        book = Book(title=req.title, author=req.author, subtitle=req.subtitle, series=req.series,
                    language=req.language, description=req.description, rights=req.rights,
                    identifier=req.identifier, own_front_matter=req.own_front_matter, chapters=_sections(req.chapters),
                    front_matter=_sections(req.front_matter), back_matter=_sections(req.back_matter))
        cover_path = root / "cover-input.img"
        cover_path.write_bytes(cover)
        checklist = build(book, cover_path, root / "out", trim=req.trim, paper=req.paper,
                          keywords=req.keywords, back_text=req.back_text)
    except BookError as e:
        tmp.cleanup()
        return _error(422, "invalid_book", str(e))
    except Exception as e:  # unreadable image etc.
        tmp.cleanup()
        return _error(422, "build_failed", f"{type(e).__name__}: {e}")
    jid = uuid.uuid4().hex
    _jobs[jid] = {"created": time.time(), "tmp": tmp, "dir": root / "out", "checklist": checklist}
    return _job_view(jid)


def _job_view(jid: str) -> dict:
    job = _jobs[jid]
    return {"id": jid, "status": "done", "expires_in_seconds": max(0, int(JOB_TTL_SECONDS - (time.time() - job["created"]))),
            "checklist": job["checklist"],
            "files": {name: f"/v1/books/{jid}/files/{name}" for name in FILES}}


@app.get("/v1/books/{job_id}")
def get_book(job_id: str):
    _sweep()
    if job_id not in _jobs:
        return _error(404, "not_found", "unknown or expired job id; create a new one with POST /v1/books")
    return _job_view(job_id)


@app.get("/v1/books/{job_id}/files/{name}")
def get_file(job_id: str, name: str):
    _sweep()
    if job_id not in _jobs:
        return _error(404, "not_found", "unknown or expired job id; create a new one with POST /v1/books")
    if name not in FILES:
        raise HTTPException(404, f"file must be one of {sorted(FILES)}")
    return FileResponse(_jobs[job_id]["dir"] / name, media_type=FILES[name], filename=name)


@app.get("/v1/spine")
def spine(pages: int, paper: str = "white"):
    if paper not in ("white", "cream") or pages < 1:
        return _error(422, "invalid_input", "pages must be >= 1 and paper 'white' or 'cream'")
    return {"pages": pages, "paper": paper, "spine_in": spine_width_in(pages, paper)}


@app.get("/v1/trim-sizes")
def trim_sizes():
    return {"trim_sizes": {k: list(v) for k, v in TRIM_SIZES.items()}}


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_BODY_BYTES:
        return _error(413, "too_large", f"request body exceeds {MAX_BODY_BYTES} bytes; shrink the cover image or split the manuscript")
    return await call_next(request)


@app.get("/v1/limits")
def limits():
    return LIMITS


@app.get("/v1/pricing")
def pricing():
    return access.pricing()


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/llms.txt", response_class=PlainTextResponse)
def llms_txt():
    return LLMS_TXT


@app.get("/quickstart.txt", response_class=PlainTextResponse)
def quickstart():
    return QUICKSTART
