import json
import asyncio
from io import BytesIO

import fitz
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.core.config import settings
from app.main import app
from app.core.limits import PdfConcurrencyLimit


client = TestClient(app)


def sample(pages=1):
    with fitz.open() as document:
        for _ in range(pages):
            document.new_page(width=400, height=500)
        return document.tobytes()


def upload(data, name="sample.pdf", endpoint="info", fields=None, other=None):
    files = [("file", (name, data, "application/pdf"))]
    if other:
        files.extend(other)
    return client.post(f"/api/pdf/{endpoint}", files=files, data=fields or {})


@pytest.mark.parametrize("name,data", [("../secret.txt", b"%PDF-bad"), ("bad.pdf", b"not a PDF"), ("broken.pdf", b"%PDF-broken")])
def test_invalid_pdf_does_not_expose_internal_details(name, data):
    response = upload(data, name)
    assert response.status_code == 400
    assert "Traceback" not in response.text
    assert "/volume1/" not in response.text


def test_encrypted_pdf_rejected():
    writer = PdfWriter()
    writer.add_blank_page(width=400, height=500)
    writer.encrypt("secret-password")
    buffer = BytesIO()
    writer.write(buffer)
    response = upload(buffer.getvalue())
    assert response.status_code == 400
    assert "Encrypted PDFs" in response.text


def test_upload_and_page_limits(monkeypatch):
    monkeypatch.setattr(settings, "max_upload_mb", 1)
    response = upload(b"%PDF-" + b"X" * 1_048_576)
    assert response.status_code == 413
    monkeypatch.setattr(settings, "max_upload_mb", 30)
    monkeypatch.setattr(settings, "max_pages", 1)
    response = upload(sample(2))
    assert response.status_code == 413


@pytest.mark.parametrize("edit", [
    {"type": "text", "page": 1, "x": 1.1, "y": 0.3, "text": "X", "size": 12, "color": "#000000"},
    {"type": "text", "page": 1, "x": 0.1, "y": 0.3, "text": "X" * 251, "size": 12, "color": "#000000"},
    {"type": "image", "page": 1, "x": 0.9, "y": 0.3, "w": 0.2, "h": 0.2, "image": 0},
])
def test_invalid_edit_rejected(edit):
    response = upload(sample(), endpoint="content-edit", fields={"edits": json.dumps([edit])})
    assert response.status_code == 400
    assert "/volume1/" not in response.text


def test_bad_font_and_image_uploads_rejected():
    text = {"type": "text", "page": 1, "x": 0.1, "y": 0.5, "text": "한글", "size": 12, "color": "#000000"}
    response = upload(sample(), endpoint="content-edit", fields={"edits": json.dumps([text])}, other=[("font", ("bad.ttf", b"invalid font data", "font/ttf"))])
    assert response.status_code == 400
    image = {"type": "image", "page": 1, "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2, "image": 0}
    response = upload(sample(), endpoint="content-edit", fields={"edits": json.dumps([image])}, other=[("images", ("bad.png", b"not an image", "image/png"))])
    assert response.status_code == 400


def test_attachment_name_is_fixed_for_uploaded_filename():
    edit = {"type": "text", "page": 1, "x": 0.1, "y": 0.5, "text": "Safe", "size": 12, "color": "#000000"}
    response = upload(sample(), name="../../source.pdf", endpoint="content-edit", fields={"edits": json.dumps([edit])})
    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="content-edited.pdf"'


def test_large_page_render_is_rejected_before_pixmap_allocation(monkeypatch):
    data = fitz.open()
    data.new_page(width=12000, height=12000)
    pdf_data = data.tobytes()
    data.close()
    def forbidden(*args, **kwargs):
        raise AssertionError("Pixmap allocation was attempted")
    monkeypatch.setattr(fitz.Page, "get_pixmap", forbidden)
    response = upload(pdf_data, endpoint="render", fields={"page": "1", "dpi": "72"})
    assert response.status_code == 413
    assert response.json()["detail"] == "Rendered image is too large"


def test_image_count_is_rejected_before_reading_assets():
    image = {"type": "image", "page": 1, "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2, "image": 0}
    assets = [("images", (f"item-{number}.png", b"not an image", "image/png")) for number in range(21)]
    response = upload(sample(), endpoint="content-edit", fields={"edits": json.dumps([image])}, other=assets)
    assert response.status_code == 400
    assert response.json()["detail"] == "Image upload limit exceeded"


def test_pdf_concurrency_limit_returns_429_and_recovers():
    async def scenario():
        entered = asyncio.Event()
        release = asyncio.Event()
        async def inner(scope, receive, send):
            entered.set()
            await release.wait()
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})
        limiter = PdfConcurrencyLimit(inner, 1)
        async def run(path):
            messages = []
            async def receive():
                return {"type": "http.request", "body": b"", "more_body": False}
            async def send(message):
                messages.append(message)
            await limiter({"type": "http", "path": path}, receive, send)
            return messages
        first = asyncio.create_task(run("/api/pdf/info"))
        await entered.wait()
        rejected = await run("/api/pdf/render")
        assert rejected[0]["status"] == 429
        assert limiter.active == 1
        release.set()
        assert (await first)[0]["status"] == 200
        assert (await run("/api/pdf/info"))[0]["status"] == 200
        assert limiter.active == 0
    asyncio.run(scenario())


def test_pdf_concurrency_limit_releases_slot_after_failure():
    async def scenario():
        async def failing(scope, receive, send):
            raise RuntimeError("test failure")
        limiter = PdfConcurrencyLimit(failing, 1)
        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}
        async def send(message):
            pass
        with pytest.raises(RuntimeError):
            await limiter({"type": "http", "path": "/api/pdf/info"}, receive, send)
        assert limiter.active == 0
    asyncio.run(scenario())
