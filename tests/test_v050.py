from io import BytesIO
import fitz
from fastapi.testclient import TestClient
from PIL import Image
from app.main import app

client = TestClient(app)


def sample():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello PDF Toolkit")
    data = doc.tobytes()
    doc.close()
    return data


def test_text_extraction():
    response = client.post("/api/pdf/text", files={"file": ("a.pdf", sample(), "application/pdf")})
    assert response.status_code == 200
    assert "Hello PDF Toolkit" in response.content.decode("utf-8")


def test_text_invalid_pages():
    response = client.post("/api/pdf/text", files={"file": ("a.pdf", sample(), "application/pdf")}, data={"pages": "5"})
    assert response.status_code == 400


def test_image_watermark():
    image = Image.new("RGB", (50, 30), "red")
    stream = BytesIO()
    image.save(stream, format="PNG")
    response = client.post("/api/pdf/image-watermark", files={"file": ("a.pdf", sample(), "application/pdf"), "image": ("a.png", stream.getvalue(), "image/png")})
    assert response.status_code == 200
    with fitz.open(stream=response.content, filetype="pdf") as doc:
        assert len(doc) == 1
        assert len(doc[0].get_images()) > 0


def test_image_watermark_invalid():
    response = client.post("/api/pdf/image-watermark", files={"file": ("a.pdf", sample(), "application/pdf"), "image": ("a.png", b"bad", "image/png")})
    assert response.status_code == 400


def test_unicode_watermark_rejects_invalid_font():
    response = client.post("/api/pdf/unicode-watermark", files={"file": ("a.pdf", sample(), "application/pdf"), "font": ("a.ttf", b"bad", "application/octet-stream")}, data={"text": "Hello"})
    assert response.status_code == 400
