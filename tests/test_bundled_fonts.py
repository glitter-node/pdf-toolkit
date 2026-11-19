import json
from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient

from app.core.fonts import FONTS
from app.main import app


client = TestClient(app)


def source_pdf(pages=1):
    with fitz.open() as document:
        for _ in range(pages):
            document.new_page(width=420, height=520)
        return document.tobytes()


def edit(text="한글 English 123\n다음 줄", page=1):
    return {"type": "text", "page": page, "x": 0.1, "y": 0.5, "w": 0.8, "h": 0.3, "text": text, "size": 18, "color": "#123456"}


def post_edit(font_id=None, upload=None, edits=None, pages=1):
    data = {"edits": json.dumps(edits or [edit()], ensure_ascii=False)}
    if font_id is not None:
        data["font_id"] = font_id
    files = [("file", ("sample.pdf", source_pdf(pages), "application/pdf"))]
    if upload is not None:
        files.append(("font", ("custom.ttf", upload, "font/ttf")))
    return client.post("/api/pdf/content-edit", data=data, files=files)


@pytest.mark.parametrize("font_id,expected", [(None, "NotoSansKR"), ("default", "NotoSansKR"), ("noto-serif-kr", "NotoSerifKR"), ("nanum-gothic", "NanumGothic")])
def test_exported_font_and_text(font_id, expected):
    response = post_edit(font_id, edits=[edit(), edit("둘째 페이지", 2)], pages=2)
    assert response.status_code == 200, response.text
    with fitz.open(stream=response.content, filetype="pdf") as document:
        assert len(document) == 2
        assert "한글 English 123" in document[0].get_text().replace("\xa0", " ")
        assert "다음 줄" in document[0].get_text().replace("\xa0", " ")
        assert "둘째 페이지" in document[1].get_text().replace("\xa0", " ")
        assert all(any(expected.lower() in font[3].lower().replace(" ", "") for font in page.get_fonts()) for page in document)


def test_upload_compatibility_and_validation():
    custom = Path("tests/fixtures/NanumGothic-Regular.ttf").read_bytes()
    assert post_edit(upload=custom).status_code == 200
    assert post_edit("upload", custom).status_code == 200
    assert post_edit("upload").status_code == 400
    assert post_edit("missing").status_code == 400
    assert post_edit("default", custom).status_code == 400
    assert post_edit("upload", b"x" * 1000).status_code == 400
    assert post_edit("default", edits=[edit("한글 😀")]).status_code == 400


def test_explicit_font_applies_to_ascii_and_legacy_ascii_keeps_builtin():
    for font_id, expected in [(None, "Helvetica"), ("default", "NotoSansKR"), ("noto-serif-kr", "NotoSerifKR")]:
        response = post_edit(font_id, edits=[edit("Plain English")])
        assert response.status_code == 200
        with fitz.open(stream=response.content, filetype="pdf") as document:
            assert any(expected.lower() in font[3].lower().replace(" ", "") for font in document[0].get_fonts())
            if font_id is None:
                assert "Plain English" in document[0].get_text()


def test_replacement_and_styled_ascii():
    replacement = {"type": "replace", "page": 1, "x": 0.1, "y": 0.1, "w": 0.8, "h": 0.08, "text": "교체 한글", "size": 18, "color": "#000000"}
    styled = edit("Bold English")
    styled["bold"] = True
    response = post_edit(edits=[replacement, styled])
    assert response.status_code == 200, response.text
    with fitz.open(stream=response.content, filetype="pdf") as document:
        text = document[0].get_text().replace("\xa0", " ")
        assert "교체 한글" in text
        assert "Bold English" in text
        assert any("Helvetica-Bold" in font[3] for font in document[0].get_fonts())
    styled["text"] = "굵은 한글"
    assert post_edit(edits=[styled]).status_code == 400


def test_missing_default_font(monkeypatch):
    monkeypatch.setitem(FONTS, "default", ("Noto Sans KR", Path("app/assets/fonts/missing.ttf").resolve()))
    assert post_edit().status_code == 503


@pytest.mark.parametrize("font_id", [None, "default", "noto-serif-kr", "nanum-gothic"])
def test_unicode_watermark(font_id):
    data = {"text": "한글 Watermark"}
    if font_id is not None:
        data["font_id"] = font_id
    response = client.post("/api/pdf/unicode-watermark", data=data, files={"file": ("sample.pdf", source_pdf(), "application/pdf")})
    assert response.status_code == 200, response.text
    with fitz.open(stream=response.content, filetype="pdf") as document:
        assert "한글 Watermark" in document[0].get_text().replace("\xa0", " ")


def test_watermark_upload_and_invalid_selection():
    files = [("file", ("sample.pdf", source_pdf(), "application/pdf")), ("font", ("custom.ttf", Path("tests/fixtures/NanumGothic-Regular.ttf").read_bytes(), "font/ttf"))]
    response = client.post("/api/pdf/unicode-watermark", data={"text": "한글 Watermark"}, files=files)
    assert response.status_code == 200
    with fitz.open(stream=response.content, filetype="pdf") as document:
        assert "한글" in document[0].get_text()
    assert client.post("/api/pdf/unicode-watermark", data={"text": "한글", "font_id": "upload"}, files={"file": ("sample.pdf", source_pdf(), "application/pdf")}).status_code == 400
    assert client.post("/api/pdf/unicode-watermark", data={"text": "한글", "font_id": "missing"}, files={"file": ("sample.pdf", source_pdf(), "application/pdf")}).status_code == 400


def test_font_route_and_locale_keys():
    html = client.get("/").text
    for control in ("content-font-id", "unicode-font-id"):
        assert f'id="{control}"' in html
    for font_id in FONTS:
        assert html.count(f'value="{font_id}"') >= 2
    assert client.get("/api/fonts/default").headers["content-type"].startswith("font/ttf")
    assert client.get("/api/fonts/../../missing").status_code != 200
    paths = list(Path("app/static/locales").glob("*.json"))
    catalogs = [json.loads(path.read_text()) for path in paths]
    assert all(set(catalog) == set(catalogs[0]) for catalog in catalogs)
