import json
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from app.core.config import settings
from app.core.security import read_pdf
from app.core.fonts import select_font
from app.services import pdf

router = APIRouter(prefix="/api/pdf", tags=["PDF"])


def attachment(data: bytes, filename: str, media_type: str = "application/pdf") -> Response:
    return Response(data, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@router.post("/merge")
async def merge(files: list[UploadFile] = File(...)):
    if not 2 <= len(files) <= settings.max_files:
        raise HTTPException(400, "Invalid file count")
    documents = [await read_pdf(file) for file in files]
    return attachment(pdf.merge(documents), "merged.pdf")


@router.post("/extract")
async def extract(file: UploadFile = File(...), pages: str = Form(...)):
    return attachment(pdf.extract(await read_pdf(file), pages), "extracted.pdf")


@router.post("/split")
async def split(file: UploadFile = File(...), pages: str | None = Form(None), mode: str = Form("single")):
    return attachment(pdf.split_archive(await read_pdf(file), pages, mode), "split.zip", "application/zip")


@router.post("/rotate")
async def rotate(file: UploadFile = File(...), angle: int = Form(...), pages: str | None = Form(None)):
    return attachment(pdf.rotate(await read_pdf(file), angle, pages), "rotated.pdf")


@router.post("/render")
async def render(file: UploadFile = File(...), page: int = Form(1), image_format: str = Form("png"), dpi: int = Form(120)):
    data, media_type = pdf.render(await read_pdf(file), page, image_format, dpi)
    return attachment(data, f"page-{page}.{'jpg' if image_format == 'jpeg' else 'png'}", media_type)


@router.post("/info")
async def info(file: UploadFile = File(...)):
    return pdf.document_info(await read_pdf(file))


@router.post("/thumbnail")
async def thumbnail(file: UploadFile = File(...), page: int = Form(...)):
    return Response(pdf.thumbnail(await read_pdf(file), page), media_type="image/png", headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@router.post("/organize")
async def organize(file: UploadFile = File(...), operations: str = Form(...)):
    try:
        parsed = json.loads(operations)
    except (ValueError, TypeError) as exc:
        raise HTTPException(400, "Invalid page operations JSON") from exc
    return attachment(pdf.organize(await read_pdf(file), parsed), "organized.pdf")



@router.post("/compress")
async def compress(file: UploadFile = File(...)):
    return attachment(pdf.optimize(await read_pdf(file)), "compressed.pdf")


@router.post("/watermark")
async def watermark(file: UploadFile = File(...), text: str = Form(...), font_size: int = Form(36), opacity: float = Form(0.25), position: str = Form("center")):
    return attachment(pdf.watermark(await read_pdf(file), text, font_size, opacity, position), "watermarked.pdf")


@router.post("/protect")
async def protect(file: UploadFile = File(...), password: str = Form(...)):
    return attachment(pdf.protect(await read_pdf(file), password), "protected.pdf")


@router.post("/text")
async def text_extract(file: UploadFile = File(...), pages: str | None = Form(None)):
    return attachment(pdf.extract_text(await read_pdf(file), pages), "extracted.txt", "text/plain; charset=utf-8")


@router.post("/unicode-watermark")
async def add_unicode_watermark(file: UploadFile = File(...), font: UploadFile | None = File(None), font_id: str | None = Form(None), text: str = Form(...), font_size: int = Form(36), opacity: float = Form(0.25), position: str = Form("center")):
    font_data = None
    if font is not None:
        if not (font.filename or "").lower().endswith((".ttf", ".otf")):
            raise HTTPException(400, "TTF or OTF font required")
        font_data = await font.read(10_000_001)
        if len(font_data) > 10_000_000:
            raise HTTPException(413, "Font upload limit exceeded")
    return attachment(pdf.unicode_watermark(await read_pdf(file), text, select_font(font_id, font_data), font_size, opacity, position), "unicode-watermarked.pdf")


@router.post("/image-watermark")
async def add_image_watermark(file: UploadFile = File(...), image: UploadFile = File(...), scale: float = Form(0.3), opacity: float = Form(0.3), position: str = Form("center")):
    image_data = await image.read(10_000_001)
    return attachment(pdf.image_watermark(await read_pdf(file), image_data, scale, opacity, position), "image-watermarked.pdf")


@router.post("/content-edit")
async def edit_content(file: UploadFile = File(...), edits: str = Form(...), font: UploadFile | None = File(None), images: list[UploadFile] | None = File(None), font_id: str | None = Form(None)):
    try:
        parsed = json.loads(edits)
    except (ValueError, TypeError) as exc:
        raise HTTPException(400, "Invalid content edits JSON") from exc
    font_data = None
    if font is not None:
        if not (font.filename or "").lower().endswith((".ttf", ".otf")):
            raise HTTPException(400, "TTF or OTF font required")
        font_data = await font.read(10_000_001)
        if len(font_data) > 10_000_000:
            raise HTTPException(413, "Font upload limit exceeded")
    if len(images or []) > 20:
        raise HTTPException(400, "Image upload limit exceeded")
    image_data = []
    for image in images or []:
        if not (image.filename or "").lower().endswith((".png", ".jpg", ".jpeg")):
            raise HTTPException(400, "PNG or JPEG image required")
        data = await image.read(10_000_001)
        if len(data) > 10_000_000 or sum(map(len, image_data)) + len(data) > 30_000_000:
            raise HTTPException(413, "Image upload limit exceeded")
        image_data.append(data)
    return attachment(pdf.content_edit(await read_pdf(file), parsed, select_font(font_id, font_data), image_data, font_for_ascii=font_id is not None or font_data is not None), "content-edited.pdf")
