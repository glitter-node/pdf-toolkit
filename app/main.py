from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.routers.pdf import router
from app.core.config import settings
from app.core.limits import PdfConcurrencyLimit
from app.core.headers import SecurityHeaders
from app.core.version import APP_VERSION
from app.core.fonts import available_fonts, bundled_font
from fastapi import HTTPException

BASE = Path(__file__).resolve().parent
app = FastAPI(title="PDF Toolkit", version=APP_VERSION, docs_url=None, redoc_url=None)
app.add_middleware(PdfConcurrencyLimit, limit=settings.max_concurrent_pdf_requests)
app.add_middleware(SecurityHeaders)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
app.include_router(router)
templates = Jinja2Templates(directory=BASE / "templates")


@app.get("/healthz")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"app_version": APP_VERSION, "bundled_fonts": available_fonts()})


@app.get("/api/fonts/{font_id}", include_in_schema=False)
def font_asset(font_id: str):
    if font_id == "upload":
        raise HTTPException(404, "Font unavailable")
    return Response(bundled_font(font_id), media_type="font/ttf")


@app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
def docs(request: Request):
    return templates.TemplateResponse(request, "docs.html")


@app.get("/redoc", response_class=HTMLResponse, include_in_schema=False)
def redoc(request: Request):
    return templates.TemplateResponse(request, "redoc.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(BASE / "static" / "favicon.ico", media_type="image/x-icon")


@app.get("/robots.txt", include_in_schema=False)
def robots():
    content = "User-agent: *\nDisallow: /api/\nDisallow: /docs\nDisallow: /redoc\nDisallow: /openapi.json\nDisallow: /static/\nSitemap: https://pdf-toolkit.glitter.kr/sitemap.xml\n"
    return PlainTextResponse(content, headers={"Cache-Control": "public, max-age=3600"})


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap():
    content = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://pdf-toolkit.glitter.kr/</loc></url></urlset>'
    return Response(content=content, media_type="application/xml", headers={"Cache-Control": "public, max-age=3600"})
