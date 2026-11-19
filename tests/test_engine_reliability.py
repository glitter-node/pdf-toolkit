from io import BytesIO
from pathlib import Path

import fitz
import pytest
import reportlab
from fastapi import HTTPException
from PIL import Image
from pypdf import PdfReader

from app.services.pdf import content_edit


def text_edit():
    return {"type": "text", "page": 1, "x": 0.25, "y": 0.5, "w": 0.5, "h": 0.25, "text": "Position", "size": 18, "color": "#000000", "align": "left", "valign": "top"}


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
@pytest.mark.parametrize("cropped", [False, True])
def test_visual_coordinates_with_rotation_and_cropbox(rotation, cropped):
    with fitz.open() as document:
        page = document.new_page(width=500, height=600)
        if cropped:
            page.set_cropbox(fitz.Rect(50, 60, 350, 460))
        page.set_rotation(rotation)
        width, height = page.rect.width, page.rect.height
        original = document.tobytes()
    result = content_edit(original, [text_edit()])
    assert result != original
    assert len(PdfReader(BytesIO(result), strict=True).pages) == 1
    with fitz.open(stream=result, filetype="pdf") as document:
        page = document[0]
        visual = page.search_for("Position")[0] * page.rotation_matrix
        assert abs(visual.x0 - width * 0.25) < 2
        assert abs(visual.y0 - height * 0.25) < 8
        assert page.rotation == rotation


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_image_visual_rectangle_on_rotated_pages(rotation):
    with fitz.open() as document:
        page = document.new_page(width=400, height=500)
        page.set_rotation(rotation)
        width, height = page.rect.width, page.rect.height
        original = document.tobytes()
    image = Image.new("RGB", (20, 10), "red")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    edit = {"type": "image", "page": 1, "x": 0.2, "y": 0.3, "w": 0.4, "h": 0.2, "image": 0, "rotation": 90}
    result = content_edit(original, [edit], images=[buffer.getvalue()])
    with fitz.open(stream=result, filetype="pdf") as document:
        page = document[0]
        rect = page.get_image_rects(page.get_images()[0][0])[0] * page.rotation_matrix
        assert abs(rect.x0 - width * 0.2) < 1
        assert abs(rect.y0 - height * 0.3) < 1
        assert abs(rect.width - width * 0.4) < 1
        assert abs(rect.height - height * 0.2) < 1


def test_actual_font_width_wraps_long_word_without_losing_characters():
    with fitz.open() as document:
        document.new_page(width=400, height=500)
        original = document.tobytes()
    word = "W" * 32
    edit = dict(text_edit(), x=0.1, y=0.9, w=0.25, h=0.7, text=word)
    result = content_edit(original, [edit])
    with fitz.open(stream=result, filetype="pdf") as document:
        page = document[0]
        assert "".join(page.get_text().split()) == word
        words = page.get_text("words")
        assert len(words) > 1
        assert all(item[2] <= 141 for item in words)


def test_unicode_font_is_embedded_and_missing_glyphs_are_rejected():
    font = Path(reportlab.__file__).resolve().parent / "fonts" / "Vera.ttf"
    with fitz.open() as document:
        document.new_page(width=400, height=500)
        original = document.tobytes()
    edit = dict(text_edit(), text="Café Ω 123")
    result = content_edit(original, [edit], font_data=font.read_bytes())
    with fitz.open(stream=result, filetype="pdf") as document:
        assert "Café Ω 123" in document[0].get_text()
        assert any("Vera" in item[3] for item in document[0].get_fonts())
    with pytest.raises(HTTPException) as error:
        content_edit(original, [dict(edit, text="한글")], font_data=font.read_bytes())
    assert error.value.status_code == 400
    assert "font" in error.value.detail.lower()


def test_redaction_removes_target_and_preserves_nearby_text():
    with fitz.open() as document:
        page = document.new_page(width=400, height=500)
        page.insert_text((40, 80), "SECRET")
        page.insert_text((40, 120), "NEARBY")
        original = document.tobytes()
    edit = {"type": "replace", "page": 1, "x": 0.09, "y": 0.13, "w": 0.3, "h": 0.08, "text": ""}
    result = content_edit(original, [edit])
    with fitz.open(stream=result, filetype="pdf") as document:
        text = document[0].get_text()
        assert "SECRET" not in text
        assert "NEARBY" in text
    with fitz.open(stream=original, filetype="pdf") as document:
        assert "SECRET" in document[0].get_text()
    assert len(PdfReader(BytesIO(result), strict=True).pages) == 1
