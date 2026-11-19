from io import BytesIO

import fitz
import pytest
from fastapi import HTTPException
from PIL import Image
from pypdf import PdfReader

from app.services.pdf import content_edit


def source():
    with fitz.open() as document:
        first = document.new_page(width=400, height=500)
        first.insert_text((40, 60), "Original secret")
        second = document.new_page(width=700, height=300)
        second.insert_text((50, 80), "Preserved page")
        return document.tobytes()


def image_data():
    image = Image.new("RGB", (24, 12), "red")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_multiline_text_geometry_and_unedited_page_integrity():
    edit = {"type": "text", "page": 1, "x": 0.2, "y": 0.55, "w": 0.6, "h": 0.25, "text": "First line\nSecond line", "size": 18, "color": "#000000", "align": "left", "valign": "top", "leading": 1.5}
    result = content_edit(source(), [edit])
    assert len(PdfReader(BytesIO(result), strict=True).pages) == 2
    with fitz.open(stream=result, filetype="pdf") as document:
        assert len(document) == 2
        assert document[1].get_text().strip() == "Preserved page"
        first = document[0].search_for("First line")[0]
        second = document[0].search_for("Second line")[0]
        assert abs(first.x0 - 80) < 2
        assert abs(first.y0 - 150) < 8
        assert 20 < second.y0 - first.y0 < 30


def test_image_over_redaction_is_preserved_and_positioned():
    edits = [
        {"type": "image", "page": 1, "x": 0.1, "y": 0.07, "w": 0.4, "h": 0.15, "image": 0, "rotation": 90},
        {"type": "replace", "page": 1, "x": 0.08, "y": 0.07, "w": 0.7, "h": 0.12, "text": ""},
    ]
    result = content_edit(source(), edits, images=[image_data()])
    with fitz.open(stream=result, filetype="pdf") as document:
        page = document[0]
        assert "Original secret" not in page.get_text()
        assert len(page.get_images()) == 1
        rect = page.get_image_rects(page.get_images()[0][0])[0]
        assert abs(rect.x0 - 40) < 1
        assert abs(rect.y0 - 35) < 1
        assert abs(rect.width - 160) < 1
        assert abs(rect.height - 75) < 1
    assert len(PdfReader(BytesIO(result), strict=True).pages) == 2


def test_rotated_page_uses_visual_preview_coordinates():
    with fitz.open() as document:
        page = document.new_page(width=400, height=500)
        page.set_rotation(90)
        original = document.tobytes()
    edit = {"type": "text", "page": 1, "x": 0.25, "y": 0.5, "w": 0.4, "h": 0.25, "text": "Rotated text", "size": 18, "color": "#000000", "align": "left", "valign": "top"}
    result = content_edit(original, [edit])
    with fitz.open(stream=result, filetype="pdf") as document:
        page = document[0]
        assert page.rotation == 90
        word = page.search_for("Rotated text")[0] * page.rotation_matrix
        assert abs(word.x0 - 125) < 2
        assert abs(word.y0 - 100) < 8
    assert len(PdfReader(BytesIO(result), strict=True).pages) == 1


def test_rotated_page_image_keeps_visual_position_and_orientation():
    with fitz.open() as document:
        page = document.new_page(width=400, height=500)
        page.set_rotation(90)
        original = document.tobytes()
    image = Image.new("RGB", (40, 20))
    image.paste("red", (0, 0, 20, 20))
    image.paste("blue", (20, 0, 40, 20))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    edit = {"type": "image", "page": 1, "x": 0.2, "y": 0.2, "w": 0.4, "h": 0.2, "image": 0}
    result = content_edit(original, [edit], images=[buffer.getvalue()])
    with fitz.open(stream=result, filetype="pdf") as document:
        page = document[0]
        pixmap = page.get_pixmap()
        assert pixmap.pixel(110, 120) == (255, 0, 0)
        assert pixmap.pixel(280, 120) == (0, 0, 255)
        assert page.rotation == 90


@pytest.mark.parametrize("text", ["", " \n ", "bad\ttext", "x" * 251])
def test_invalid_text_is_rejected(text):
    edit = {"type": "text", "page": 1, "x": 0.1, "y": 0.5, "w": 0.8, "h": 0.3, "text": text, "size": 12, "color": "#000000"}
    with pytest.raises(HTTPException) as error:
        content_edit(source(), [edit])
    assert error.value.status_code == 400
