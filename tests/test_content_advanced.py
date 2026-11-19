from io import BytesIO
import os
from pathlib import Path
import fitz
import pytest
from PIL import Image
from fastapi import HTTPException
from pypdf import PdfReader
from app.services.pdf import content_edit


def original():
    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    page.insert_text((40, 60), "Sensitive original text")
    data = doc.tobytes()
    doc.close()
    return data


def test_replacement_redacts_original():
    edit = {"type": "replace", "page": 1, "x": 0.08, "y": 0.07, "w": 0.7, "h": 0.09, "text": "Updated text", "size": 12, "color": "#000000"}
    result = content_edit(original(), [edit])
    with fitz.open(stream=result, filetype="pdf") as doc:
        text = doc[0].get_text().replace("\xa0", " ")
        assert "Sensitive original text" not in text
        assert "Updated text" in text


def test_image_insertion():
    image = Image.new("RGB", (20, 10), (255, 0, 0))
    buffer = BytesIO()
    image.save(buffer, "PNG")
    edit = {"type": "image", "page": 1, "x": 0.4, "y": 0.4, "w": 0.3, "h": 0.2, "image": 0}
    result = content_edit(original(), [edit], images=[buffer.getvalue()])
    with fitz.open(stream=result, filetype="pdf") as doc:
        assert len(doc[0].get_images()) >= 1


def test_unicode_requires_font():
    edit = {"type": "text", "page": 1, "x": 0.4, "y": 0.4, "text": "한글", "size": 18, "color": "#000000"}
    with pytest.raises(HTTPException):
        content_edit(original(), [edit])


def test_invalid_rectangle():
    edit = {"type": "replace", "page": 1, "x": 0.9, "y": 0.4, "w": 0.3, "h": 0.2, "text": "X", "size": 18, "color": "#000000"}
    with pytest.raises(HTTPException):
        content_edit(original(), [edit])


def test_unicode_with_uploaded_font():
    path = Path(os.environ.get("PDF_TOOLKIT_TEST_KOREAN_FONT", Path(__file__).parent / "fixtures" / "NanumGothic-Regular.ttf"))
    if not path.exists():
        pytest.skip("Korean test font unavailable; set PDF_TOOLKIT_TEST_KOREAN_FONT to a locally licensed font")
    edit = {"type": "text", "page": 1, "x": 0.1, "y": 0.4, "w": 0.8, "h": 0.2, "text": "한글 English 123\n다음 줄", "size": 18, "color": "#000000"}
    result = content_edit(original(), [edit], font_data=path.read_bytes())
    with fitz.open(stream=result, filetype="pdf") as doc:
        text = doc[0].get_text()
        assert "한글 English 123" in text
        assert "다음 줄" in text
        assert doc[0].get_fonts()
    assert len(PdfReader(BytesIO(result), strict=True).pages) == 1
