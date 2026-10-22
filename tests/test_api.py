import base64
import io

from fastapi.testclient import TestClient
from PIL import Image

from pressready.api import app

client = TestClient(app)


def cover_b64():
    buf = io.BytesIO()
    Image.new("RGB", (800, 1200), (30, 90, 160)).save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


def payload(**kw):
    p = {"title": "Tiny Brave", "author": "A. Writer", "trim": "5x8", "paper": "cream",
         "chapters": [{"title": "One", "markdown": "# One\n\nHello.\n\n***\n\nAgain."},
                      {"title": "", "markdown": "# Two\n\nMore."}],
         "cover_image_base64": cover_b64()}
    p.update(kw)
    return p


def test_create_and_download():
    r = client.post("/v1/books", json=payload())
    assert r.status_code == 201, r.text
    body = r.json()
    # a tiny sample book legitimately warns (short page count, empty description)
    assert body["status"] == "done" and body["checklist"]["ok"] is False
    assert any("description" in w for w in body["checklist"]["warnings"])
    got = client.get(f"/v1/books/{body['id']}")
    assert got.status_code == 200
    epub = client.get(body["files"]["book.epub"])
    assert epub.status_code == 200 and epub.content[:2] == b"PK"
    pdf = client.get(body["files"]["interior.pdf"])
    assert pdf.content[:4] == b"%PDF"


def test_typed_errors():
    r = client.post("/v1/books", json=payload(trim="4x4"))
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_trim"
    r = client.post("/v1/books", json=payload(cover_image_base64="!!!"))
    assert r.json()["error"]["code"] == "invalid_cover"
    r = client.post("/v1/books", json=payload(author=" "))
    assert r.json()["error"]["code"] == "invalid_book"
    assert client.get("/v1/books/nope").json()["error"]["code"] == "not_found"


def test_docs_and_helpers():
    assert "PressReady" in client.get("/llms.txt").text
    assert "/v1/books" in client.get("/openapi.json").json()["paths"]
    assert client.get("/v1/spine", params={"pages": 200, "paper": "cream"}).json()["spine_in"] > 0
    assert "5x8" in client.get("/v1/trim-sizes").json()["trim_sizes"]
