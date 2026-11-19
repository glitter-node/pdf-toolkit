import json
import os
import socket
import subprocess
import sys
import time
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen

import fitz
import pytest
from PIL import Image
from playwright.sync_api import sync_playwright
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path(os.environ.get("PDF_TOOLKIT_E2E_ARTIFACTS", ROOT / "artifacts" / "e2e"))


def pdf_sample():
    with fitz.open() as document:
        for number in range(2):
            page = document.new_page(width=400, height=500)
            page.insert_text((30, 50), f"Original page {number + 1}")
        return document.tobytes()


def image_sample():
    output = BytesIO()
    Image.new("RGB", (80, 40), (220, 40, 30)).save(output, "PNG")
    return output.getvalue()


@pytest.fixture(scope="module")
def isolated_server():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    assert port != 8013
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    log = (ARTIFACTS / "server.log").open("w")
    process = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port), "--workers", "1", "--log-level", "warning"], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            if process.poll() is not None:
                raise RuntimeError("Isolated test server exited; see server.log")
            try:
                with urlopen(base + "/healthz", timeout=1) as response:
                    if response.status == 200:
                        break
            except Exception:
                time.sleep(0.1)
        else:
            raise RuntimeError("Isolated test server did not become ready")
        yield base
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        log.close()


@pytest.fixture(scope="module")
def chromium():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                yield browser
            finally:
                browser.close()
    except Exception as exc:
        (ARTIFACTS / "browser-launch-error.txt").write_text(str(exc))
        raise


def point(page, x, y):
    box = page.locator("#content-canvas").bounding_box()
    assert box and box["width"] > 0 and box["height"] > 0
    return box["x"] + box["width"] * x, box["y"] + box["height"] * y


def edit(page, index):
    return page.evaluate("index => ({...contentEdits[index]})", index)


def drag(page, start, end):
    page.mouse.move(*point(page, *start))
    page.mouse.down()
    page.mouse.move(*point(page, *end), steps=8)
    page.mouse.up()


def load_content(page, sample):
    page.locator('[data-panel="content-editor"]').click()
    page.locator("#content-file").set_input_files({"name": "sample.pdf", "mimeType": "application/pdf", "buffer": sample})
    page.locator("#content-load").click()
    page.locator("#content-status").filter(has_text="Select an editing mode to continue.").wait_for()
    assert page.locator("#content-canvas").evaluate("canvas => canvas.width > 0")


def test_release_workflow(isolated_server, chromium):
    context = chromium.new_context(viewport={"width": 1366, "height": 768}, accept_downloads=True)
    page = context.new_page()
    browser_log = []
    steps = []
    page.on("console", lambda event: browser_log.append("console: " + event.text))
    page.on("pageerror", lambda event: browser_log.append("error: " + str(event)))
    sample = pdf_sample()
    try:
        page.goto(isolated_server)
        assert page.get_by_role("heading", name="PDF Toolkit").is_visible()
        steps.append("01 main page")
        assert page.locator("#tools").is_visible()
        steps.append("02 PDF tools tab")
        page.locator('[data-panel="editor"]').click()
        assert page.locator("#editor").is_visible()
        steps.append("03 Page editor tab")
        load_content(page, sample)
        steps.extend(["04 Content editor tab", "05 PDF upload", "06 page preview"])
        page.locator("#content-font").set_input_files(str(ROOT / "tests" / "fixtures" / "NanumGothic-Regular.ttf"))
        page.wait_for_function("contentPreviewFont !== null")
        page.locator("#content-mode-text").click()
        page.mouse.click(*point(page, 0.2, 0.35))
        assert page.locator("#content-text-dialog").evaluate("dialog => dialog.open")
        steps.append("07 add text dialog")
        page.locator("#content-dialog-value").fill("한글 English 123\n둘째 줄")
        page.locator("#content-dialog-submit").click()
        page.locator("#content-count").filter(has_text="1 content edits").wait_for()
        steps.append("08 multiline Korean and English")
        page.locator("#content-mode-select").click()
        first = edit(page, 0)
        page.mouse.dblclick(*point(page, first["x"] + min(first["w"] / 2, 0.05), first["y"] - first["h"] / 2))
        assert page.locator("#content-text-dialog").evaluate("dialog => dialog.open")
        page.locator("#content-dialog-value").fill("한글 English 123\n수정한 줄")
        page.locator("#content-dialog-submit").click()
        page.wait_for_function("contentEdits[0]?.text.includes('수정한 줄')")
        assert "수정한 줄" in edit(page, 0)["text"]
        steps.append("09 edit text")
        first = edit(page, 0)
        drag(page, (first["x"] + first["w"] / 2, first["y"] - first["h"] / 2), (first["x"] + first["w"] / 2 + 0.05, first["y"] - first["h"] / 2 + 0.04))
        moved = edit(page, 0)
        assert moved["x"] != first["x"]
        steps.append("10 move text")
        drag(page, (moved["x"] + moved["w"], moved["y"]), (min(0.95, moved["x"] + moved["w"] + 0.04), min(0.95, moved["y"] + 0.04)))
        assert edit(page, 0)["manualSize"] is True
        steps.append("11 resize text box")
        page.locator("#content-image").set_input_files({"name": "image.png", "mimeType": "image/png", "buffer": image_sample()})
        page.locator("#content-mode-image").click()
        page.mouse.click(*point(page, 0.55, 0.55))
        page.locator("#content-count").filter(has_text="2 content edits").wait_for()
        steps.append("12 add image")
        page.locator("#content-mode-select").click()
        image = edit(page, 1)
        drag(page, (image["x"] + image["w"] / 2, image["y"] + image["h"] / 2), (image["x"] + image["w"] / 2 - 0.05, image["y"] + image["h"] / 2 - 0.04))
        assert edit(page, 1)["x"] != image["x"]
        steps.append("13 move image")
        image = edit(page, 1)
        drag(page, (image["x"] + image["w"], image["y"] + image["h"]), (min(0.95, image["x"] + image["w"] + 0.04), min(0.95, image["y"] + image["h"] + 0.04)))
        assert edit(page, 1)["w"] != image["w"]
        steps.append("14 resize image")
        page.locator("#content-image-rotate").click()
        assert edit(page, 1)["rotation"] == 90
        steps.append("15 rotate image")
        page.locator("#content-undo").click()
        assert edit(page, 1).get("rotation", 0) == 0
        page.locator("#content-redo").click()
        assert edit(page, 1)["rotation"] == 90
        steps.append("16 Undo and Redo")
        page.once("dialog", lambda dialog: dialog.dismiss())
        page.locator("#content-file").set_input_files({"name": "replacement.pdf", "mimeType": "application/pdf", "buffer": sample})
        assert page.locator("#content-count").inner_text() == "2 content edits"
        steps.append("17 unsaved edit warning")
        page.locator("#content-font").set_input_files([])
        page.locator("#content-save").click()
        assert "Unicode font" in page.locator("#content-status").inner_text()
        steps.append("18 pre-save validation")
        page.locator("#content-font").set_input_files(str(ROOT / "tests" / "fixtures" / "NanumGothic-Regular.ttf"))
        page.wait_for_function("contentPreviewFont !== null")
        page.route("**/api/pdf/content-edit", lambda route: route.abort(), times=1)
        page.locator("#content-save").click()
        page.locator("#content-status").filter(has_text="Connection failed").wait_for()
        assert page.locator("#content-count").inner_text() == "2 content edits"
        steps.append("19 save failure preserves edits")
        with page.expect_download() as download_info:
            page.locator("#content-save").click()
        assert download_info.value.suggested_filename == "content-edited.pdf"
        saved = ARTIFACTS / "content-edited.pdf"
        download_info.value.save_as(saved)
        with fitz.open(saved) as document:
            assert len(document) == 2
            assert "수정한 줄" in document[0].get_text().replace("\xa0", " ")
        assert len(PdfReader(saved, strict=True).pages) == 2
        assert "saved successfully" in page.locator("#content-status").inner_text()
        steps.append("20 save retry and download")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        assert page.locator("#back-to-top").is_visible()
        page.locator("#back-to-top").click()
        page.wait_for_function("window.scrollY < 10")
        steps.append("21 Top button")
        (ARTIFACTS / "workflow.json").write_text(json.dumps({"steps": steps, "console": browser_log}, indent=2))
    except Exception:
        page.screenshot(path=str(ARTIFACTS / "workflow-failure.png"), full_page=True)
        (ARTIFACTS / "workflow-failure.json").write_text(json.dumps({"steps": steps, "console": browser_log}, indent=2))
        raise
    finally:
        context.close()


@pytest.mark.parametrize("width,height", [(1920, 1080), (1366, 768), (768, 1024), (390, 844), (320, 640)])
def test_responsive_layout(isolated_server, chromium, width, height):
    context = chromium.new_context(viewport={"width": width, "height": height})
    page = context.new_page()
    try:
        page.goto(isolated_server)
        load_content(page, pdf_sample())
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 2")
        assert page.locator("#content-save").is_visible()
        page.mouse.click(*point(page, 0.25, 0.3))
        dialog = page.locator("#content-text-dialog")
        assert dialog.evaluate("element => element.open")
        box = dialog.bounding_box()
        assert box and box["x"] >= -1 and box["y"] >= -1
        assert box["x"] + box["width"] <= width + 1
        assert box["y"] + box["height"] <= height + 1
        assert page.locator("#content-dialog-submit").is_visible()
        page.locator("#content-dialog-cancel").click()
        page.screenshot(path=str(ARTIFACTS / f"viewport-{width}.png"), full_page=True)
    except Exception:
        page.screenshot(path=str(ARTIFACTS / f"viewport-{width}-failure.png"), full_page=True)
        raise
    finally:
        context.close()


def test_report_only_csp_and_local_docs(isolated_server, chromium):
    context = chromium.new_context(viewport={"width": 1366, "height": 768})
    page = context.new_page()
    violations = []
    external_requests = []
    page.on("console", lambda message: violations.append(message.text) if "content security policy" in message.text.lower() or "violates the following" in message.text.lower() else None)
    page.on("request", lambda request: external_requests.append(request.url) if request.url.startswith(("http://", "https://")) and not request.url.startswith(isolated_server + "/") else None)
    try:
        for path, marker in (("/", "#content-editor"), ("/docs", "#docs-list"), ("/redoc", "#docs-list")):
            page.goto(isolated_server + path)
            page.locator(marker).wait_for(state="attached")
            page.wait_for_load_state("networkidle")
            if path != "/":
                assert "API operations available" in page.locator("#docs-status").inner_text()
        page.goto(isolated_server)
        load_content(page, pdf_sample())
        page.locator("#content-font").set_input_files(str(ROOT / "tests" / "fixtures" / "NanumGothic-Regular.ttf"))
        page.wait_for_function("contentPreviewFont !== null")
        page.locator("#content-image").set_input_files({"name": "image.png", "mimeType": "image/png", "buffer": image_sample()})
        page.locator("#content-mode-image").click()
        page.mouse.click(*point(page, 0.4, 0.4))
        page.locator("#content-count").filter(has_text="1 content edits").wait_for()
        (ARTIFACTS / "csp-report.json").write_text(json.dumps({"violations": violations, "external_requests": external_requests}, indent=2))
        assert not violations
        assert not external_requests
    except Exception:
        page.screenshot(path=str(ARTIFACTS / "csp-failure.png"), full_page=True)
        (ARTIFACTS / "csp-report.json").write_text(json.dumps({"violations": violations, "external_requests": external_requests}, indent=2))
        raise
    finally:
        context.close()
