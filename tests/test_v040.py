from io import BytesIO
from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter
from app.main import app

client = TestClient(app)


def sample():
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=400)
    stream = BytesIO()
    writer.write(stream)
    return stream.getvalue()


def upload(endpoint, data=None):
    return client.post(f"/api/pdf/{endpoint}", files={"file": ("sample.pdf", sample(), "application/pdf")}, data=data or {})


def test_compress():
    response = upload("compress")
    assert response.status_code == 200
    assert len(PdfReader(BytesIO(response.content)).pages) == 1


def test_watermark():
    response = upload("watermark", {"text": "CONFIDENTIAL"})
    assert response.status_code == 200
    assert "CONFIDENTIAL" in PdfReader(BytesIO(response.content)).pages[0].extract_text()


def test_watermark_invalid():
    assert upload("watermark", {"text": ""}).status_code == 422
    assert upload("watermark", {"text": "TEST", "opacity": "2"}).status_code == 400


def test_protect():
    response = upload("protect", {"password": "test-password-123"})
    assert response.status_code == 200
    reader = PdfReader(BytesIO(response.content))
    assert reader.is_encrypted
    assert reader.decrypt("test-password-123")
    assert len(reader.pages) == 1


def test_protect_short_password():
    assert upload("protect", {"password": "short"}).status_code == 400
