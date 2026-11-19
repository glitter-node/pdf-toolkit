from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
import json

import fitz
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.core.headers import CONTENT_SECURITY_POLICY, SECURE_CONTENT_SECURITY_POLICY, SecurityHeaders
from app.main import app


client = TestClient(app)
root = Path(__file__).resolve().parents[1]


class ResourceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.resources = []
        self.unsafe_attributes = []
        self.inline_scripts = []
        self.inline_styles = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        for name, value in attrs:
            if name.lower() == "style" or name.lower().startswith("on"):
                self.unsafe_attributes.append((tag, name))
            if isinstance(value, str) and value.lower().startswith("javascript:"):
                self.unsafe_attributes.append((tag, name))
        if tag == "script":
            if not values.get("src"):
                self.inline_scripts.append(tag)
            else:
                self.resources.append(values["src"])
        if tag == "style":
            self.inline_styles.append(tag)
        if tag in ("img", "iframe", "source") and values.get("src"):
            self.resources.append(values["src"])
        if tag == "link" and values.get("rel") == "stylesheet":
            self.resources.append(values.get("href", ""))


def assert_security(response, cache):
    assert response.headers.get_list("content-security-policy") == [CONTENT_SECURITY_POLICY]
    assert "content-security-policy-report-only" not in response.headers
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
    assert response.headers["cross-origin-opener-policy"] == "same-origin"
    assert response.headers["cross-origin-resource-policy"] == "same-origin"
    assert response.headers["cache-control"] == cache
    assert "strict-transport-security" not in response.headers


def test_main_html_has_consistent_security_headers():
    response = client.get("/")
    assert response.status_code == 200
    assert_security(response, "no-store")
    assert '<html lang="ko">' in response.text


def test_api_success_and_error_headers():
    with fitz.open() as document:
        document.new_page(width=200, height=300)
        data = document.tobytes()
    good = client.post("/api/pdf/info", files={"file": ("sample.pdf", data, "application/pdf")})
    bad = client.post("/api/pdf/info", files={"file": ("bad.pdf", b"invalid", "application/pdf")})
    invalid = client.post("/api/pdf/content-edit", files={"file": ("sample.pdf", data, "application/pdf")}, data={"edits": "invalid"})
    missing = client.post("/api/pdf/info")
    assert good.status_code == 200
    assert bad.status_code == 400
    assert invalid.status_code == 400
    assert missing.status_code == 422
    for response in (good, bad, invalid, missing):
        assert_security(response, "no-store")
        assert "/volume1/" not in response.text


def test_options_validation_and_unhandled_errors_have_headers():
    options = client.options("/api/pdf/info", headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "POST"})
    assert options.status_code == 405
    assert_security(options, "no-store")
    assert "access-control-allow-origin" not in options.headers
    failing = FastAPI()
    failing.add_middleware(SecurityHeaders)

    @failing.get("/fail")
    def fail():
        raise RuntimeError("sensitive internal failure")

    response = TestClient(failing, raise_server_exceptions=False).get("/fail")
    assert response.status_code == 500
    assert_security(response, "no-store")
    assert response.json() == {"detail": "Internal server error"}


def test_static_assets_and_public_metadata_cache_separately():
    for path in ("/static/js/content-editor.js", "/static/css/app.css", "/favicon.ico", "/robots.txt", "/sitemap.xml"):
        response = client.get(path)
        assert response.status_code == 200
        assert_security(response, "public, max-age=3600")
    assert client.get("/static/js/content-editor.js").headers["content-type"].startswith("application/javascript")


def test_template_resources_are_local_and_no_inline_code_exists():
    for template in (root / "app" / "templates").glob("*.html"):
        parser = ResourceParser()
        parser.feed(template.read_text())
        assert not parser.unsafe_attributes
        assert not parser.inline_scripts
        assert not parser.inline_styles
        assert parser.resources
        assert all(value.startswith("/static/") or value == "/favicon.ico" for value in parser.resources)
    for path in (root / "app" / "static" / "js").glob("*.js"):
        text = path.read_text()
        for forbidden in ("eval(", "new Function(", "document.write(", "innerHTML", "insertAdjacentHTML", "javascript:"):
            assert forbidden not in text


def test_csp_is_enforced_with_minimal_blob_exceptions_without_unsafe_modes():
    assert "unsafe-inline" not in CONTENT_SECURITY_POLICY
    assert "unsafe-eval" not in CONTENT_SECURITY_POLICY
    directives = dict(item.split(" ", 1) for item in CONTENT_SECURITY_POLICY.split("; "))
    assert directives["default-src"] == "'none'"
    assert directives["script-src"] == "'self'"
    assert directives["script-src-attr"] == "'none'"
    assert directives["style-src"] == "'self'"
    assert directives["style-src-elem"] == "'self'"
    assert directives["style-src-attr"] == "'none'"
    assert directives["font-src"] == "'self' blob:"
    assert directives["img-src"] == "'self' blob:"
    assert directives["worker-src"] == "'none'"
    assert directives["connect-src"] == "'self'"
    assert directives["img-src"] == "'self' blob:"
    assert directives["media-src"] == "'none'"
    assert "data:" not in CONTENT_SECURITY_POLICY
    assert "https:" not in CONTENT_SECURITY_POLICY
    assert "*" not in CONTENT_SECURITY_POLICY
    assert "upgrade-insecure-requests" not in CONTENT_SECURITY_POLICY
    assert SECURE_CONTENT_SECURITY_POLICY.endswith("upgrade-insecure-requests")


def test_secure_forwarded_request_gets_upgrade_policy():
    secure = client.get("/", headers={"X-Forwarded-Proto": "https"})
    assert secure.headers["content-security-policy"] == SECURE_CONTENT_SECURITY_POLICY


def test_api_docs_use_local_assets_without_inline_initializers():
    for route in ("/docs", "/redoc"):
        response = client.get(route)
        assert response.status_code == 200
        assert_security(response, "no-store")
        assert "cdn.jsdelivr.net" not in response.text
        assert "fonts.googleapis.com" not in response.text
        assert "fastapi.tiangolo.com/img" not in response.text
        parser = ResourceParser()
        parser.feed(response.text)
        assert not parser.inline_scripts
        assert not parser.inline_styles
        assert not parser.unsafe_attributes
        for asset in parser.resources:
            assert client.get(asset).status_code == 200
    assert 'href="/openapi.json"' in client.get("/redoc").text


def test_docs_script_builds_schema_with_dom_nodes():
    source = (root / "app" / "static" / "js" / "docs.js").read_text()
    assert 'fetch("/openapi.json"' in source
    assert 'document.createElement("section")' in source
    assert "textContent" in source
    assert "innerHTML" not in source
    assert not (root / "app" / "static" / "vendor").exists()


def test_preview_and_pdf_download_keep_headers_and_integrity():
    with fitz.open() as document:
        document.new_page(width=200, height=300)
        data = document.tobytes()
    preview = client.post("/api/pdf/render", files={"file": ("sample.pdf", data, "application/pdf")}, data={"page": "1", "image_format": "png", "dpi": "72"})
    assert preview.status_code == 200
    assert preview.content.startswith(b"\x89PNG")
    assert_security(preview, "no-store")
    edit = {"type": "text", "page": 1, "x": 0.1, "y": 0.5, "text": "Safe", "size": 12, "color": "#000000"}
    import json
    saved = client.post("/api/pdf/content-edit", files={"file": ("sample.pdf", data, "application/pdf")}, data={"edits": json.dumps([edit])})
    assert saved.status_code == 200
    assert_security(saved, "no-store")
    assert saved.headers["content-disposition"] == 'attachment; filename="content-edited.pdf"'
    with fitz.open(stream=saved.content, filetype="pdf") as document:
        assert "Safe" in document[0].get_text()
    assert len(PdfReader(BytesIO(saved.content), strict=True).pages) == 1
