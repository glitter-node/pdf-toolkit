from io import BytesIO
import fitz
from fastapi.testclient import TestClient
from app.main import app


def test_content_preview_render_and_coordinate_mapping():
    document = fitz.open()
    page = document.new_page(width=400, height=600)
    page.insert_text((100, 300), "Reference", fontsize=18)
    source = document.tobytes()
    document.close()
    client = TestClient(app)
    response = client.post("/api/pdf/render", files={"file": ("sample.pdf", source, "application/pdf")}, data={"page": "1", "image_format": "png", "dpi": "144"})
    assert response.status_code == 200
    image = fitz.Pixmap(response.content)
    assert image.width == 800
    assert image.height == 1200
    result = client.post("/api/pdf/content-edit", files={"file": ("sample.pdf", source, "application/pdf")}, data={"edits": '[{"page":1,"x":0.25,"y":0.5,"text":"Positioned","size":18,"color":"#000000"}]'})
    assert result.status_code == 200
    with fitz.open(stream=result.content, filetype="pdf") as edited:
        words = [word for word in edited[0].get_text("words") if word[4] == "Positioned"]
        assert len(words) == 1
        assert abs(words[0][0] - 100) < 1
        assert abs(words[0][3] - 300) < 6
