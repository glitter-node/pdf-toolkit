import json
from io import BytesIO

import fitz
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.version import APP_VERSION
from test_v091 import fixture_pdf

client = TestClient(app)


def request(operations):
    return client.post("/api/pdf/organize", files={"file": ("sample.pdf", fixture_pdf(), "application/pdf")}, data={"operations": json.dumps(operations)})


def test_version_and_editor_controls():
    assert app.version == APP_VERSION
    html = client.get("/").text
    assert f"v{APP_VERSION}" in html
    assert 'id="editor-undo"' in html
    script = client.get("/static/js/editor.js").text
    assert "editorHistory" in script
    assert "editorMove" in script


@pytest.mark.parametrize("operations,expected", [
    ([{"page": 2, "rotation": 0}, {"page": 1, "rotation": 0}], ["STABLE-PAGE-2", "STABLE-PAGE-1"]),
    ([{"page": 3, "rotation": 90}], ["STABLE-PAGE-3"]),
    ([{"page": 1, "rotation": 0}, {"page": 3, "rotation": 0}], ["STABLE-PAGE-1", "STABLE-PAGE-3"]),
])
def test_editor_export_scenarios(operations, expected):
    response = request(operations)
    assert response.status_code == 200
    with fitz.open(stream=response.content, filetype="pdf") as doc:
        assert len(doc) == len(expected)
        for page, label in zip(doc, expected):
            assert label in page.get_text()


def test_reject_all_pages_removed():
    assert request([]).status_code == 400


def test_reject_non_pdf():
    response = client.post("/api/pdf/info", files={"file": ("bad.pdf", b"not a pdf", "application/pdf")})
    assert response.status_code == 400
