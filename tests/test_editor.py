import json
from io import BytesIO
from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter
from app.main import app

client = TestClient(app)

def sample():
    writer = PdfWriter()
    for width in (200, 300, 400):
        writer.add_blank_page(width=width, height=500)
    stream = BytesIO()
    writer.write(stream)
    return stream.getvalue()

def upload():
    return {"file": ("sample.pdf", sample(), "application/pdf")}

def test_info():
    response = client.post("/api/pdf/info", files=upload())
    assert response.status_code == 200
    assert response.json()["page_count"] == 3
    assert response.json()["pages"][1]["width"] == 300

def test_thumbnail():
    response = client.post("/api/pdf/thumbnail", files=upload(), data={"page": "1"})
    assert response.status_code == 200
    assert response.content.startswith(b"\x89PNG")

def test_thumbnail_invalid_page():
    assert client.post("/api/pdf/thumbnail", files=upload(), data={"page": "4"}).status_code == 400

def test_organize():
    operations = [{"page": 3, "rotation": 90}, {"page": 1, "rotation": 0}]
    response = client.post("/api/pdf/organize", files=upload(), data={"operations": json.dumps(operations)})
    assert response.status_code == 200
    reader = PdfReader(BytesIO(response.content))
    assert len(reader.pages) == 2
    assert float(reader.pages[0].mediabox.width) == 400
    assert reader.pages[0].get("/Rotate") == 90

def test_organize_duplicate():
    operations = [{"page": 1, "rotation": 0}, {"page": 1, "rotation": 90}]
    assert client.post("/api/pdf/organize", files=upload(), data={"operations": json.dumps(operations)}).status_code == 400

def test_organize_invalid_rotation():
    assert client.post("/api/pdf/organize", files=upload(), data={"operations": '[{"page":1,"rotation":45}]'}).status_code == 400

def test_organize_invalid_json():
    assert client.post("/api/pdf/organize", files=upload(), data={"operations": "invalid"}).status_code == 400
