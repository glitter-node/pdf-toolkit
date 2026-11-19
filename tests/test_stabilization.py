from io import BytesIO
from pathlib import Path
import warnings

import fitz
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfReader
import reportlab

from app.main import app


client = TestClient(app)


def sample():
    document = fitz.open()
    for number in (1, 2):
        page = document.new_page()
        page.insert_text((72, 72), f"STABILIZATION-PAGE-{number}")
    data = document.tobytes()
    document.close()
    return data


def upload(endpoint, data=None, extra_files=None):
    files = {"file": ("sample.pdf", sample(), "application/pdf")}
    if extra_files:
        files.update(extra_files)
    return client.post(f"/api/pdf/{endpoint}", files=files, data=data or {})


def assert_pdf(response, watermark=None, image=False):
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")
    assert len(PdfReader(BytesIO(response.content), strict=True).pages) == 2
    with fitz.open(stream=response.content, filetype="pdf") as document:
        for number, page in enumerate(document, 1):
            text = page.get_text()
            assert f"STABILIZATION-PAGE-{number}" in text
            if watermark:
                assert watermark in text
            if image:
                assert page.get_images()


def test_optimize_preserves_content_without_removed_argument_warnings():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        response = upload("compress")
    assert_pdf(response)
    assert len(response.content) <= len(sample())
    assert not any("remove_identicals" in str(item.message) or "remove_orphans" in str(item.message) for item in caught)


def test_text_watermark_preserves_content_and_adds_text():
    assert_pdf(upload("watermark", {"text": "AUDIT MARK"}), watermark="AUDIT MARK")


def test_image_watermark_preserves_content_and_adds_images():
    stream = BytesIO()
    Image.new("RGB", (20, 20), "red").save(stream, format="PNG")
    assert_pdf(upload("image-watermark", extra_files={"image": ("mark.png", stream.getvalue(), "image/png")}), image=True)


def test_unicode_watermark_with_valid_font_preserves_content():
    font = Path(reportlab.__file__).resolve().parent / "fonts" / "Vera.ttf"
    assert_pdf(upload("unicode-watermark", {"text": "Audit"}, {"font": ("Vera.ttf", font.read_bytes(), "font/ttf")}), watermark="Audit")


def test_render_png_and_jpeg_are_valid_images():
    for image_format, expected in (("png", "PNG"), ("jpeg", "JPEG")):
        response = upload("render", {"page": "2", "image_format": image_format})
        assert response.status_code == 200
        with Image.open(BytesIO(response.content)) as image:
            assert image.format == expected
            image.verify()
