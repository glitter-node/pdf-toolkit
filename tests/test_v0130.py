from io import BytesIO

import fitz
import pytest
from fastapi import HTTPException
from PIL import Image

from app.services.pdf import content_edit


def document():
    with fitz.open() as pdf:
        pdf.new_page(width=400, height=500)
        return pdf.tobytes()


def text_edit(**kwargs):
    return {"type": "text", "page": 1, "x": 0.1, "y": 0.5, "w": 0.8, "h": 0.3, "text": "Formatting", "size": 18, "color": "#18243b", **kwargs}


@pytest.mark.parametrize("align", ["left", "center", "right"])
@pytest.mark.parametrize("valign", ["top", "middle", "bottom"])
def test_alignment_and_spacing(align, valign):
    result = content_edit(document(), [text_edit(align=align, valign=valign, leading=1.4)])
    with fitz.open(stream=result, filetype="pdf") as pdf:
        rect = pdf[0].search_for("Formatting")[0]
        assert rect.x0 >= 39
        assert rect.x1 <= 361
        assert rect.y0 >= 98
        assert rect.y1 <= 251


@pytest.mark.parametrize("bold,italic", [(True, False), (False, True), (True, True)])
def test_builtin_font_styles(bold, italic):
    result = content_edit(document(), [text_edit(bold=bold, italic=italic)])
    with fitz.open(stream=result, filetype="pdf") as pdf:
        assert "Formatting" in pdf[0].get_text()


@pytest.mark.parametrize("field,value", [("align", "diagonal"), ("valign", "baseline"), ("leading", 0.5), ("leading", 2.1), ("bold", "true")])
def test_invalid_formatting(field, value):
    with pytest.raises(HTTPException) as error:
        content_edit(document(), [text_edit(**{field: value})])
    assert error.value.status_code == 400


def test_image_rotation():
    image = Image.new("RGB", (30, 20), "red")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    result = content_edit(document(), [{"type": "image", "page": 1, "x": 0.2, "y": 0.2, "w": 0.3, "h": 0.2, "image": 0, "rotation": 90}], images=[buffer.getvalue()])
    with fitz.open(stream=result, filetype="pdf") as pdf:
        assert len(pdf[0].get_images()) == 1


def test_invalid_image_rotation():
    image = Image.new("RGB", (20, 20))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    with pytest.raises(HTTPException) as error:
        content_edit(document(), [{"type": "image", "page": 1, "x": 0.2, "y": 0.2, "w": 0.3, "h": 0.2, "image": 0, "rotation": 45}], images=[buffer.getvalue()])
    assert error.value.status_code == 400
