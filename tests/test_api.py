from io import BytesIO
from zipfile import ZipFile
from fastapi.testclient import TestClient
from pypdf import PdfWriter, PdfReader
from app.main import app

client = TestClient(app)


def sample(pages=3):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=300)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_health():
    assert client.get("/healthz").json() == {"status": "ok"}


def test_merge():
    response = client.post("/api/pdf/merge", files=[("files", ("a.pdf", sample(2), "application/pdf")), ("files", ("b.pdf", sample(1), "application/pdf"))])
    assert response.status_code == 200
    assert len(PdfReader(BytesIO(response.content)).pages) == 3


def test_extract():
    response = client.post("/api/pdf/extract", files={"file": ("a.pdf", sample(), "application/pdf")}, data={"pages": "1,3"})
    assert response.status_code == 200
    assert len(PdfReader(BytesIO(response.content)).pages) == 2


def test_reject_invalid():
    response = client.post("/api/pdf/extract", files={"file": ("a.pdf", b"bad", "application/pdf")}, data={"pages": "1"})
    assert response.status_code == 400


def test_split_single_all():
    response = client.post("/api/pdf/split", files={"file": ("a.pdf", sample(3), "application/pdf")})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    with ZipFile(BytesIO(response.content)) as archive:
        assert len(archive.namelist()) == 3
        assert all(len(PdfReader(BytesIO(archive.read(name))).pages) == 1 for name in archive.namelist())

def test_split_ranges():
    response = client.post("/api/pdf/split", files={"file": ("a.pdf", sample(3), "application/pdf")}, data={"mode": "ranges", "pages": "1-2,3"})
    assert response.status_code == 200
    with ZipFile(BytesIO(response.content)) as archive:
        assert [len(PdfReader(BytesIO(archive.read(name))).pages) for name in archive.namelist()] == [2, 1]

def test_split_invalid_mode():
    response = client.post("/api/pdf/split", files={"file": ("a.pdf", sample(2), "application/pdf")}, data={"mode": "unknown"})
    assert response.status_code == 400

def test_split_invalid_range():
    response = client.post("/api/pdf/split", files={"file": ("a.pdf", sample(2), "application/pdf")}, data={"mode": "ranges", "pages": "1-3"})
    assert response.status_code == 400
