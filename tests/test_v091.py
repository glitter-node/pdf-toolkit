import json
from io import BytesIO

import fitz
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter

from app.main import app

client = TestClient(app)


def fixture_pdf():
    document = fitz.open()
    for index, width in enumerate((250, 350, 450), 1):
        page = document.new_page(width=width, height=600)
        page.insert_text((35, 55), f"STABLE-PAGE-{index}")
        page.insert_link({"kind": fitz.LINK_URI, "from": fitz.Rect(30, 75, 170, 100), "uri": f"https://example.org/page/{index}"})
    raw = document.tobytes()
    document.close()
    reader = PdfReader(BytesIO(raw))
    writer = PdfWriter()
    writer.append(reader)
    writer.add_metadata({"/Title": "Stability fixture", "/Author": "PDF Toolkit"})
    writer.pages[0].rotate(90)
    stream = BytesIO()
    writer.write(stream)
    return stream.getvalue()


def post(path, data):
    return client.post(path, files={"file": ("fixture.pdf", fixture_pdf(), "application/pdf")}, data=data)


def assert_page(document, index, label, expected_rotation, width, height):
    page = document[index]
    assert page.rotation == expected_rotation
    assert (round(page.rect.width), round(page.rect.height)) == (width, height)
    assert label in page.get_text()
    links = page.get_links()
    assert len(links) == 1
    assert links[0]["uri"] == f"https://example.org/page/{label.rsplit('-', 1)[1]}"


def test_organize_reorder_rotate_delete_preserves_content_links_and_metadata():
    operations = [{"page": 3, "rotation": 270}, {"page": 1, "rotation": 90}]
    response = post("/api/pdf/organize", {"operations": json.dumps(operations)})
    assert response.status_code == 200
    reader = PdfReader(BytesIO(response.content))
    assert reader.metadata.title == "Stability fixture"
    assert reader.metadata.author == "PDF Toolkit"
    with fitz.open(stream=response.content, filetype="pdf") as document:
        assert len(document) == 2
        assert_page(document, 0, "STABLE-PAGE-3", 270, 600, 450)
        assert_page(document, 1, "STABLE-PAGE-1", 180, 250, 600)


@pytest.mark.parametrize("angle,expected,dimensions", [(90, 180, (250, 600)), (180, 270, (600, 250)), (270, 0, (250, 600))])
def test_rotate_existing_rotation(angle, expected, dimensions):
    response = post("/api/pdf/rotate", {"angle": str(angle), "pages": "1"})
    assert response.status_code == 200
    with fitz.open(stream=response.content, filetype="pdf") as document:
        assert len(document) == 3
        assert_page(document, 0, "STABLE-PAGE-1", expected, *dimensions)
        assert_page(document, 1, "STABLE-PAGE-2", 0, 350, 600)


@pytest.mark.parametrize("operations", [[], [{"page": 1, "rotation": 0}, {"page": 1, "rotation": 90}], [{"page": True, "rotation": 0}], [{"page": 1, "rotation": True}], [{"page": 1, "rotation": -90}], [{"page": 4, "rotation": 0}], [{"page": 1, "rotation": 0, "extra": 1}]])
def test_organize_rejects_invalid_operations(operations):
    response = post("/api/pdf/organize", {"operations": json.dumps(operations)})
    assert response.status_code == 400


def test_organize_rejects_invalid_json():
    assert post("/api/pdf/organize", {"operations": "not-json"}).status_code == 400


def test_organize_zero_rotation_retains_original_rotation():
    response = post("/api/pdf/organize", {"operations": json.dumps([{"page": 1, "rotation": 0}])})
    assert response.status_code == 200
    with fitz.open(stream=response.content, filetype="pdf") as document:
        assert_page(document, 0, "STABLE-PAGE-1", 90, 600, 250)
