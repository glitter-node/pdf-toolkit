from io import BytesIO
import fitz
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app
from app.services.pdf import content_edit


def sample():
    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    page.insert_text((30, 40), "Original content")
    data = doc.tobytes()
    doc.close()
    return data


def test_content_edit_preserves_original_and_adds_text():
    result = content_edit(sample(), [{"page": 1, "x": 0.25, "y": 0.5, "text": "Added content", "size": 20, "color": "#112233"}])
    with fitz.open(stream=result, filetype="pdf") as doc:
        assert len(doc) == 1
        text = doc[0].get_text()
        assert "Original content" in text
        assert "Added content" in text


@pytest.mark.parametrize("change", [
    {"page": 2}, {"x": -0.1}, {"y": 1.1}, {"size": 90},
    {"color": "red"}, {"text": "한글"}, {"text": ""}, {"x": float("nan")}
])
def test_content_edit_rejects_invalid_edits(change):
    edit = {"page": 1, "x": 0.25, "y": 0.5, "text": "Added", "size": 18, "color": "#000000"}
    edit.update(change)
    with pytest.raises(HTTPException) as exc:
        content_edit(sample(), [edit])
    assert exc.value.status_code == 400


def test_content_edit_api():
    client = TestClient(app)
    response = client.post("/api/pdf/content-edit", files={"file": ("sample.pdf", sample(), "application/pdf")}, data={"edits": '[{"page":1,"x":0.25,"y":0.5,"text":"API text","size":18,"color":"#000000"}]'})
    assert response.status_code == 200
    with fitz.open(stream=response.content, filetype="pdf") as doc:
        assert "API text" in doc[0].get_text()


def test_content_edit_rejects_empty():
    with pytest.raises(HTTPException):
        content_edit(sample(), [])
