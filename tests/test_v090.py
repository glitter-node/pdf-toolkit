from fastapi.testclient import TestClient
from app.main import app
from app.core.version import APP_VERSION

client = TestClient(app)


def test_favicon():
    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert response.content[:4] == b"\x00\x00\x01\x00"


def test_robots():
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert "Disallow: /api/" in response.text
    assert "Sitemap: https://pdf-toolkit.glitter.kr/sitemap.xml" in response.text


def test_sitemap():
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert "https://pdf-toolkit.glitter.kr/" in response.text
    assert "/api/" not in response.text


def test_v090_ui():
    response = client.get("/")
    assert response.status_code == 200
    assert f"v{APP_VERSION}" in response.text
    assert 'id="merge-list"' in response.text
    assert 'href="/favicon.ico"' in response.text
