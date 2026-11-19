import io
import json
import sys
from pathlib import Path

import fitz
import httpx
import pytest

sys.modules["httpx2"] = httpx

from fastapi.testclient import TestClient

from app.core import fonts
from app.main import app


CLIENT = TestClient(app)
FONT = fonts.BUNDLED_FONT.read_bytes()


def blank_pdf(pages=1):
    document = fitz.open()
    for _ in range(pages):
        document.new_page()
    data = document.tobytes()
    document.close()
    return data


def post_content(edits, font_id=None, uploaded=None, pages=1):
    data = {"edits": json.dumps(edits)}
    if font_id is not None:
        data["font_id"] = font_id
    files = [("file", ("input.pdf", blank_pdf(pages), "application/pdf"))]
    if uploaded is not None:
        files.append(("font", ("custom.ttf", uploaded, "font/ttf")))
    return CLIENT.post("/api/pdf/content-edit", data=data, files=files)


def text_edit(text, page=1):
    return {"type": "text", "page": page, "x": 0.1, "y": 0.3, "text": text, "size": 18, "color": "#18243b"}


@pytest.mark.parametrize("font_id", [None, "default", "upload"])
def test_korean_content_embeds_font(font_id):
    response = post_content([text_edit("한글 English\n두 번째 줄")], font_id, FONT if font_id == "upload" else None)
    assert response.status_code == 200, response.text
    with fitz.open(stream=response.content, filetype="pdf") as document:
        assert "한글 English" in document[0].get_text()
        assert "두 번째 줄" in document[0].get_text()
        assert "NanumGothic" in document[0].get_fonts(full=True)[0][3]
        assert document[0].get_pixmap().samples


def test_legacy_font_upload_and_multiple_pages():
    response = post_content([text_edit("한글 A", 1), text_edit("한글 B", 2)], uploaded=FONT, pages=2)
    assert response.status_code == 200, response.text
    with fitz.open(stream=response.content, filetype="pdf") as document:
        assert len(document) == 2
        assert "한글 A" in document[0].get_text()
        assert "한글 B" in document[1].get_text()


def test_font_validation_and_listing(monkeypatch, tmp_path):
    assert [entry["id"] for entry in CLIENT.get("/api/pdf/fonts").json()["fonts"]] == ["default"]
    preview = CLIENT.get("/api/pdf/fonts/default/file")
    assert preview.status_code == 200
    assert preview.headers["content-type"].startswith("font/ttf")
    assert preview.content[:4] == b"\x00\x01\x00\x00"
    edit = [text_edit("한글")]
    assert post_content(edit, "upload").status_code == 400
    assert post_content(edit, "missing").status_code == 400
    assert post_content(edit, "default", FONT).status_code == 400
    monkeypatch.setattr(fonts.settings, "pdf_font_noto_serif_kr_path", str(tmp_path / "missing.ttf"))
    assert [entry["id"] for entry in CLIENT.get("/api/pdf/fonts").json()["fonts"]] == ["default"]
    assert post_content(edit, "noto-serif-kr").status_code == 503
    assert CLIENT.get("/api/pdf/fonts/../../app/core/config.py/file").status_code in (400, 404)


def test_optional_font_id_uses_configured_file(monkeypatch, tmp_path):
    path = tmp_path / "optional.ttf"
    path.write_bytes(FONT)
    monkeypatch.setattr(fonts.settings, "pdf_font_noto_serif_kr_path", str(path))
    listing = CLIENT.get("/api/pdf/fonts").json()["fonts"]
    assert [entry["id"] for entry in listing] == ["default", "noto-serif-kr"]
    response = post_content([text_edit("한글")], "noto-serif-kr")
    assert response.status_code == 200, response.text
    with fitz.open(stream=response.content, filetype="pdf") as document:
        assert "한글" in document[0].get_text()
        assert "NanumGothic" in document[0].get_fonts(full=True)[0][3]
    watermark = CLIENT.post("/api/pdf/unicode-watermark", data={"text": "한글", "font_id": "noto-serif-kr"}, files={"file": ("input.pdf", blank_pdf(), "application/pdf")})
    assert watermark.status_code == 200, watermark.text
    with fitz.open(stream=watermark.content, filetype="pdf") as document:
        assert "한글" in document[0].get_text()


def test_locale_font_keys_match():
    root = Path(__file__).resolve().parents[1] / "app/static/locales"
    catalogs = [json.loads((root / f"{language}.json").read_text()) for language in ("ko", "en", "ja", "zh-CN")]
    assert all(set(catalog) == set(catalogs[0]) for catalog in catalogs[1:])


def test_watermark_default_and_upload():
    for data in ({"font_id": "default"}, {}):
        files = [("file", ("input.pdf", blank_pdf(), "application/pdf"))]
        if not data:
            files.append(("font", ("custom.ttf", FONT, "font/ttf")))
        response = CLIENT.post("/api/pdf/unicode-watermark", data={"text": "한글", **data}, files=files)
        assert response.status_code == 200, response.text
        with fitz.open(stream=response.content, filetype="pdf") as document:
            assert "한글" in document[0].get_text()
            assert "NanumGothic" in document[0].get_fonts(full=True)[0][3]


def test_replacement_text_uses_default_font():
    edit = {"type": "replace", "page": 1, "x": 0.1, "y": 0.4, "w": 0.3, "h": 0.2, "text": "한글 교체", "size": 18, "color": "#18243b"}
    response = post_content([edit])
    assert response.status_code == 200, response.text
    with fitz.open(stream=response.content, filetype="pdf") as document:
        assert "한글 교체" in document[0].get_text()
