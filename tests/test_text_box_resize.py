import fitz
import pytest
from fastapi import HTTPException
from app.services.pdf import content_edit


def test_text_box_export_and_overflow():
    source = fitz.open()
    source.new_page(width=600, height=800)
    data = source.tobytes()
    source.close()
    edit = {"type": "text", "page": 1, "x": 0.1, "y": 0.3, "w": 0.5, "h": 0.15, "text": "Resize box text", "size": 18, "color": "#111111"}
    result = content_edit(data, [edit])
    with fitz.open(stream=result, filetype="pdf") as output:
        assert "Resize box text" in output[0].get_text()
    with pytest.raises(HTTPException) as exc:
        content_edit(data, [dict(edit, w=0.03, h=0.02)])
    assert exc.value.status_code == 400
