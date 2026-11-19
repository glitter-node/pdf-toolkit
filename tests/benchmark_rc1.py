import json
import os
from io import BytesIO
from pathlib import Path
from time import perf_counter
from urllib.parse import urlsplit

import fitz
import httpx
from PIL import Image
from pypdf import PdfReader


BASE = os.environ.get("PDF_TOOLKIT_BENCHMARK_URL", "http://127.0.0.1:18013")
ADDRESS = urlsplit(BASE)
if ADDRESS.hostname not in ("127.0.0.1", "localhost") or ADDRESS.port == 8013:
    raise SystemExit("Benchmark requires an isolated loopback server outside port 8013")


def rss_mb():
    pid = os.environ.get("PDF_TOOLKIT_BENCHMARK_PID")
    if not pid:
        return None
    status = Path(f"/proc/{pid}/status")
    if not status.exists():
        return None
    for line in status.read_text().splitlines():
        if line.startswith("VmRSS:"):
            return round(int(line.split()[1]) / 1024, 1)
    return None


def sample(count, image=False, rotated=False):
    with fitz.open() as document:
        for index in range(count):
            page = document.new_page(width=400, height=500)
            page.insert_text((40, 70), f"Benchmark page {index + 1}")
            if rotated:
                page.set_rotation(90)
            if image:
                picture = Image.new("RGB", (80, 60), (180, 60, 50))
                buffer = BytesIO()
                picture.save(buffer, format="PNG")
                page.insert_image(fitz.Rect(80, 100, 240, 220), stream=buffer.getvalue())
        return document.tobytes()


def timed_request(client, path, data, fields=None, font=None):
    files = [("file", ("sample.pdf", data, "application/pdf"))]
    if font:
        files.append(("font", ("NanumGothic-Regular.ttf", font, "font/ttf")))
    start = perf_counter()
    response = client.post(path, files=files, data=fields or {})
    duration = round((perf_counter() - start) * 1000, 1)
    if response.status_code != 200:
        raise RuntimeError(f"{path}: {response.status_code} {response.text[:180]}")
    return response, duration


font_data = (Path(__file__).parent / "fixtures" / "NanumGothic-Regular.ttf").read_bytes()
cases = [("1 page", sample(1), False), ("10 pages", sample(10), False), ("50 pages", sample(50), False), ("100 pages", sample(100), False), ("image", sample(1, image=True), False), ("Unicode", sample(1), True), ("rotated", sample(1, rotated=True), False)]
print("| Case | Upload/info ms | Preview ms | Edit/save ms | PDF bytes | RSS MB |")
print("|---|---:|---:|---:|---:|---:|")
with httpx.Client(base_url=BASE, timeout=120) as client:
    for name, data, unicode_text in cases:
        info, upload_ms = timed_request(client, "/api/pdf/info", data)
        _, preview_ms = timed_request(client, "/api/pdf/render", data, {"page": "1", "image_format": "png", "dpi": "144"})
        edit = {"type": "text", "page": 1, "x": 0.1, "y": 0.45, "w": 0.75, "h": 0.2, "text": "한글 English 123\n다음 줄" if unicode_text else "Release check", "size": 16, "color": "#000000"}
        saved, save_ms = timed_request(client, "/api/pdf/content-edit", data, {"edits": json.dumps([edit])}, font_data if unicode_text else None)
        with fitz.open(stream=saved.content, filetype="pdf") as result:
            assert len(result) == info.json()["page_count"]
        assert len(PdfReader(BytesIO(saved.content), strict=True).pages) == info.json()["page_count"]
        print(f"| {name} | {upload_ms} | {preview_ms} | {save_ms} | {len(saved.content)} | {rss_mb()} |")
    before = rss_mb()
    for _ in range(10):
        timed_request(client, "/api/pdf/content-edit", cases[0][1], {"edits": json.dumps([{"type": "text", "page": 1, "x": 0.1, "y": 0.5, "text": "Repeat", "size": 12, "color": "#000000"}])})
    print(f"Repeated saves: 10; RSS before: {before} MB; RSS after: {rss_mb()} MB")
