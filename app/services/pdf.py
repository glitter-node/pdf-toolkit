from io import BytesIO
from inspect import signature
from math import ceil, isfinite
from zipfile import ZipFile, ZIP_DEFLATED
import fitz
from fastapi import HTTPException
from pypdf import PdfReader, PdfWriter
from app.core.config import settings


def load_reader(data: bytes) -> PdfReader:
    try:
        reader = PdfReader(BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise HTTPException(400, "Encrypted PDFs are not supported")
        if len(reader.pages) > settings.max_pages:
            raise HTTPException(413, "Page count limit exceeded")
        return reader
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, "Invalid PDF document") from exc


def serialize(writer: PdfWriter) -> bytes:
    stream = BytesIO()
    writer.write(stream)
    return stream.getvalue()


def merge(documents: list[bytes]) -> bytes:
    writer = PdfWriter()
    total = 0
    for data in documents:
        reader = load_reader(data)
        total += len(reader.pages)
        if total > settings.max_pages:
            raise HTTPException(413, "Page count limit exceeded")
        writer.append(reader)
    return serialize(writer)


def extract(data: bytes, pages: str) -> bytes:
    reader = load_reader(data)
    indices = parse_pages(pages, len(reader.pages))
    writer = PdfWriter()
    for index in indices:
        writer.add_page(reader.pages[index])
    return serialize(writer)


def parse_pages(expression: str, count: int) -> list[int]:
    selected = []
    try:
        for token in expression.split(","):
            token = token.strip()
            if "-" in token:
                parts = token.split("-")
                if len(parts) != 2:
                    raise ValueError
                start, end = map(int, parts)
                if start > end:
                    raise ValueError
                selected.extend(range(start, end + 1))
            else:
                selected.append(int(token))
    except ValueError as exc:
        raise HTTPException(400, "Invalid page selection") from exc
    if not selected or len(selected) > settings.max_pages or any(p < 1 or p > count for p in selected):
        raise HTTPException(400, "Page selection out of range")
    return [p - 1 for p in selected]


def rotate(data: bytes, angle: int, pages: str | None) -> bytes:
    if angle not in (90, 180, 270):
        raise HTTPException(400, "Rotation must be 90, 180, or 270")
    reader = load_reader(data)
    indices = set(parse_pages(pages, len(reader.pages))) if pages else set(range(len(reader.pages)))
    writer = PdfWriter()
    writer.append(reader)
    for index in indices:
        writer.pages[index].rotate(angle)
    if reader.metadata:
        writer.add_metadata({key: str(value) for key, value in reader.metadata.items() if isinstance(key, str) and value is not None})
    return serialize(writer)


def render(data: bytes, page: int, image_format: str, dpi: int) -> tuple[bytes, str]:
    load_reader(data)
    if image_format not in ("png", "jpeg") or dpi < 72 or dpi > 200:
        raise HTTPException(400, "Invalid image settings")
    try:
        with fitz.open(stream=data, filetype="pdf") as document:
            if page < 1 or page > len(document):
                raise HTTPException(400, "Page selection out of range")
            bounds = document[page - 1].rect
            scale = dpi / 72
            if (ceil(bounds.width * scale) + 2) * (ceil(bounds.height * scale) + 2) > 25_000_000:
                raise HTTPException(413, "Rendered image is too large")
            pixmap = document[page - 1].get_pixmap(dpi=dpi, alpha=False)
            if pixmap.width * pixmap.height > 25_000_000:
                raise HTTPException(413, "Rendered image is too large")
            return pixmap.tobytes("jpg" if image_format == "jpeg" else "png"), "image/jpeg" if image_format == "jpeg" else "image/png"
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, "Unable to render PDF") from exc


def split_archive(data: bytes, pages: str | None = None, mode: str = "single") -> bytes:
    reader = load_reader(data)
    if mode not in ("single", "ranges"):
        raise HTTPException(400, "Invalid split mode")
    if pages is None or not pages.strip():
        if mode == "ranges":
            raise HTTPException(400, "Page ranges are required")
        selections = [[index] for index in range(len(reader.pages))]
    elif mode == "single":
        selections = [[index] for index in parse_pages(pages, len(reader.pages))]
    else:
        selections = []
        total = 0
        for expression in pages.split(","):
            if not expression.strip():
                raise HTTPException(400, "Invalid page range")
            indices = parse_pages(expression, len(reader.pages))
            if len(set(indices)) != len(indices):
                raise HTTPException(400, "Duplicate pages in range")
            selections.append(indices)
            total += len(indices)
            if total > settings.max_pages:
                raise HTTPException(413, "Page count limit exceeded")
    if not selections or len(selections) > settings.max_pages:
        raise HTTPException(400, "Invalid page selection")
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for number, indices in enumerate(selections, 1):
            writer = PdfWriter()
            for index in indices:
                writer.add_page(reader.pages[index])
            name = f"page-{indices[0] + 1:04d}.pdf" if mode == "single" else f"part-{number:04d}.pdf"
            if mode == "single" and len(indices) != 1:
                raise HTTPException(400, "Invalid single page selection")
            archive.writestr(name if mode == "ranges" else f"part-{number:04d}-{name}", serialize(writer))
    return output.getvalue()



def document_info(data: bytes) -> dict:
    load_reader(data)
    try:
        with fitz.open(stream=data, filetype="pdf") as document:
            return {"page_count": len(document), "pages": [{"page": index + 1, "width": round(page.rect.width, 2), "height": round(page.rect.height, 2)} for index, page in enumerate(document)]}
    except Exception as exc:
        raise HTTPException(400, "Unable to inspect PDF") from exc


def thumbnail(data: bytes, page: int) -> bytes:
    load_reader(data)
    try:
        with fitz.open(stream=data, filetype="pdf") as document:
            if page < 1 or page > len(document):
                raise HTTPException(400, "Page selection out of range")
            rect = document[page - 1].rect
            if rect.width <= 0 or rect.height <= 0:
                raise HTTPException(400, "Invalid page dimensions")
            scale = min(1.0, 240 / max(rect.width, rect.height))
            pixmap = document[page - 1].get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            if pixmap.width * pixmap.height > 250_000:
                raise HTTPException(413, "Thumbnail is too large")
            return pixmap.tobytes("png")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, "Unable to render thumbnail") from exc


def organize(data: bytes, operations: list[dict]) -> bytes:
    reader = load_reader(data)
    if not isinstance(operations, list) or not operations or len(operations) > len(reader.pages):
        raise HTTPException(400, "Invalid page operations")
    seen = set()
    writer = PdfWriter()
    for item in operations:
        if not isinstance(item, dict) or set(item) != {"page", "rotation"}:
            raise HTTPException(400, "Invalid page operation")
        page = item["page"]
        rotation = item["rotation"]
        if type(page) is not int or page < 1 or page > len(reader.pages) or page in seen:
            raise HTTPException(400, "Invalid or duplicate page")
        if type(rotation) is not int or rotation not in (0, 90, 180, 270):
            raise HTTPException(400, "Invalid page rotation")
        seen.add(page)
        writer.add_page(reader.pages[page - 1])
        if rotation:
            writer.pages[-1].rotate(rotation)
    if reader.metadata:
        writer.add_metadata({key: str(value) for key, value in reader.metadata.items() if isinstance(key, str) and value is not None})
    return serialize(writer)



def optimize(data: bytes) -> bytes:
    reader = load_reader(data)
    writer = PdfWriter()
    writer.append(reader)
    for page in writer.pages:
        page.compress_content_streams()
    params = signature(writer.compress_identical_objects).parameters
    if "remove_duplicates" in params:
        writer.compress_identical_objects(remove_duplicates=True, remove_unreferenced=True)
    else:
        writer.compress_identical_objects(remove_identicals=True, remove_orphans=True)
    result = serialize(writer)
    return result if len(result) < len(data) else data


def watermark(data: bytes, text: str, font_size: int = 36, opacity: float = 0.25, position: str = "center") -> bytes:
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import Color
    reader = load_reader(data)
    if not text or len(text) > 120 or any(ord(ch) < 32 or ord(ch) > 126 for ch in text):
        raise HTTPException(400, "Watermark text must be 1-120 printable ASCII characters")
    if font_size < 8 or font_size > 100 or not 0.05 <= opacity <= 1 or position not in ("center", "top", "bottom"):
        raise HTTPException(400, "Invalid watermark settings")
    writer = PdfWriter()
    for page in reader.pages:
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        overlay = BytesIO()
        layer = canvas.Canvas(overlay, pagesize=(width, height))
        layer.setFillColor(Color(0.25, 0.25, 0.25, alpha=opacity))
        layer.setFont("Helvetica", font_size)
        x = width / 2
        y = height / 2 if position == "center" else height - font_size * 1.5 if position == "top" else font_size * 1.5
        layer.drawCentredString(x, y, text)
        layer.save()
        overlay.seek(0)
        writer.add_page(page)
        writer.pages[-1].merge_page(PdfReader(overlay).pages[0])
    return serialize(writer)


def protect(data: bytes, password: str) -> bytes:
    reader = load_reader(data)
    if not 8 <= len(password) <= 128 or len(password.encode("utf-8")) > 256:
        raise HTTPException(400, "Password must contain 8-128 characters")
    writer = PdfWriter()
    writer.append(reader)
    try:
        writer.encrypt(user_password=password, owner_password=password, algorithm="AES-256")
        return serialize(writer)
    except ImportError as exc:
        raise HTTPException(503, "AES encryption dependency unavailable") from exc



def extract_text(data: bytes, pages: str | None = None) -> bytes:
    reader = load_reader(data)
    indices = parse_pages(pages, len(reader.pages)) if pages else list(range(len(reader.pages)))
    try:
        with fitz.open(stream=data, filetype="pdf") as document:
            sections = [document[index].get_text("text", sort=True) for index in indices]
            return ("\n\n".join(sections)).encode("utf-8")
    except Exception as exc:
        raise HTTPException(400, "Unable to extract text") from exc


def unicode_watermark(data: bytes, text: str, font_data: bytes, font_size: int = 36, opacity: float = 0.25, position: str = "center") -> bytes:
    load_reader(data)
    if not text.strip() or len(text) > 120 or any(ord(char) < 32 for char in text):
        raise HTTPException(400, "Invalid watermark text")
    if not 8 <= font_size <= 100 or not 0.05 <= opacity <= 1 or position not in ("center", "top", "bottom"):
        raise HTTPException(400, "Invalid watermark settings")
    if not font_data or len(font_data) > 30_000_000:
        raise HTTPException(400, "Invalid font file")
    try:
        with fitz.open(stream=data, filetype="pdf") as document:
            font = fitz.Font(fontbuffer=font_data)
            if any(not font.has_glyph(ord(char)) for char in text):
                raise HTTPException(400, "Selected font does not contain every requested character")
            for page in document:
                page.insert_font(fontname="UserFont", fontbuffer=font_data)
                width = font.text_length(text, fontsize=font_size)
                x = (page.rect.width - width) / 2
                y = page.rect.height / 2 if position == "center" else font_size * 1.5 if position == "top" else page.rect.height - font_size * 1.5
                page.insert_text((x, y), text, fontsize=font_size, fontname="UserFont", color=(0.25, 0.25, 0.25), fill_opacity=opacity, overlay=True)
            return document.tobytes(garbage=3, deflate=True)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, "Unable to apply Unicode watermark or unsupported font") from exc


def image_watermark(data: bytes, image_data: bytes, scale: float = 0.3, opacity: float = 0.3, position: str = "center") -> bytes:
    from PIL import Image, UnidentifiedImageError
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    load_reader(data)
    if not 0.05 <= scale <= 1 or not 0.05 <= opacity <= 1 or position not in ("center", "top", "bottom"):
        raise HTTPException(400, "Invalid watermark settings")
    if not image_data or len(image_data) > 10_000_000:
        raise HTTPException(413, "Image size limit exceeded")
    try:
        with Image.open(BytesIO(image_data)) as source:
            if source.format not in ("PNG", "JPEG") or source.width * source.height > 12_000_000:
                raise HTTPException(400, "Unsupported image or image dimensions")
            image = source.convert("RGBA")
            image.putalpha(image.getchannel("A").point(lambda value: round(value * opacity)))
        reader = load_reader(data)
        writer = PdfWriter()
        for page in reader.pages:
            width, height = float(page.mediabox.width), float(page.mediabox.height)
            target_width = width * scale
            target_height = target_width * image.height / image.width
            if target_height > height * 0.9:
                target_height = height * 0.9
                target_width = target_height * image.width / image.height
            x = (width - target_width) / 2
            y = (height - target_height) / 2 if position == "center" else height - target_height - 12 if position == "top" else 12
            overlay = BytesIO()
            layer = canvas.Canvas(overlay, pagesize=(width, height))
            layer.drawImage(ImageReader(image), x, y, target_width, target_height, mask="auto")
            layer.save()
            overlay.seek(0)
            writer.add_page(page)
            writer.pages[-1].merge_page(PdfReader(overlay).pages[0])
        return serialize(writer)
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(400, "Invalid watermark image") from exc


def content_edit(data: bytes, edits: list[dict], font_data: bytes | None = None, images: list[bytes] | None = None, font_for_ascii: bool = True) -> bytes:
    load_reader(data)
    if not isinstance(edits, list) or not 1 <= len(edits) <= 200:
        raise HTTPException(400, "Provide 1 to 200 content edits")
    images = images or []
    if len(images) > 20 or sum(map(len, images)) > 30_000_000:
        raise HTTPException(400, "Image upload limit exceeded")
    if font_data is not None and (not 1000 <= len(font_data) <= 30_000_000):
        raise HTTPException(400, "Invalid font file size")
    try:
        with fitz.open(stream=data, filetype="pdf") as document:
            font_metrics = fitz.Font(fontbuffer=font_data) if font_data else None
            replacements = []
            deferred_text = []
            deferred_images = []
            for edit in edits:
                if not isinstance(edit, dict):
                    raise HTTPException(400, "Invalid content edit")
                kind = edit.get("type", "text")
                if kind not in ("text", "image", "replace"):
                    raise HTTPException(400, "Invalid content edit type")
                page_number = edit.get("page")
                if type(page_number) is not int or not 1 <= page_number <= len(document):
                    raise HTTPException(400, "Invalid content page")
                x, y = edit.get("x"), edit.get("y")
                if not all(type(v) in (int, float) and isfinite(v) and 0 <= v <= 1 for v in (x, y)):
                    raise HTTPException(400, "Invalid content coordinates")
                page = document[page_number - 1]
                if kind in ("image", "replace"):
                    w, h = edit.get("w"), edit.get("h")
                    if not all(type(v) in (int, float) and isfinite(v) and 0 < v <= 1 for v in (w, h)) or x + w > 1.000001 or y + h > 1.000001:
                        raise HTTPException(400, "Invalid content rectangle")
                    rect = fitz.Rect(x * page.rect.width, y * page.rect.height, (x + w) * page.rect.width, (y + h) * page.rect.height) * page.derotation_matrix
                    if kind == "image":
                        index = edit.get("image")
                        if type(index) is not int or not 0 <= index < len(images):
                            raise HTTPException(400, "Invalid image reference")
                        try:
                            with fitz.open(stream=images[index], filetype="png") as _:
                                pass
                        except Exception:
                            try:
                                with fitz.open(stream=images[index], filetype="jpeg") as _:
                                    pass
                            except Exception as exc:
                                raise HTTPException(400, "Invalid image data") from exc
                        rotation = edit.get("rotation", 0)
                        if type(rotation) is not int or rotation not in (0, 90, 180, 270):
                            raise HTTPException(400, "Invalid image rotation")
                        deferred_images.append((page_number, rect, index, rotation))
                        continue
                    replacements.append((page_number, rect, edit))
                    page.add_redact_annot(rect, fill=(1, 1, 1), cross_out=False)
                    continue
                deferred_text.append((page_number, edit))
            for page_number in sorted({number for number, _, _ in replacements}):
                page = document[page_number - 1]
                page.apply_redactions(images=2, graphics=1, text=0)
            for page_number, rect, index, rotation in deferred_images:
                page = document[page_number - 1]
                page.insert_image(rect, stream=images[index], keep_proportion=False, overlay=True, rotate=(rotation + page.rotation) % 360)
            for page_number, edit in deferred_text:
                _insert_content_text(document[page_number - 1], edit, font_data, font_metrics, font_for_ascii)
            for page_number, rect, edit in replacements:
                if edit.get("text"):
                    page = document[page_number - 1]
                    visual = rect * page.rotation_matrix
                    replacement = dict(edit, x=visual.x0 / page.rect.width, y=(visual.y0 + min(visual.height, float(edit.get("size", 18)) * 1.2)) / page.rect.height)
                    _insert_content_text(page, replacement, font_data, font_metrics, font_for_ascii)
            return document.tobytes(garbage=4, deflate=True)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, "Unable to edit PDF content") from exc


def _wrap_content_text(text: str, width: float, font, size: float) -> str:
    lines = []
    for paragraph in text.split("\n"):
        current = ""
        for char in paragraph:
            candidate = current + char
            if current and font.text_length(candidate, fontsize=size) > width:
                lines.append(current)
                current = char
            else:
                current = candidate
        lines.append(current)
    return "\n".join(lines)


def _insert_content_text(page, edit: dict, font_data: bytes | None, font_metrics=None, font_for_ascii: bool = True) -> None:
    text, size, color = edit.get("text"), edit.get("size"), edit.get("color")
    if not isinstance(text, str) or not 1 <= len(text) <= 250 or not text.strip() or any((ord(c) < 32 and c != "\n") or ord(c) == 127 for c in text):
        raise HTTPException(400, "Text must contain 1 to 250 printable characters or line breaks")
    if type(size) not in (int, float) or not isfinite(size) or not 6 <= size <= 72:
        raise HTTPException(400, "Invalid font size")
    if not isinstance(color, str) or len(color) != 7 or color[0] != "#" or any(c not in "0123456789abcdefABCDEF" for c in color[1:]):
        raise HTTPException(400, "Invalid text color")
    if any(ord(c) > 126 for c in text) and not font_data:
        raise HTTPException(400, "Upload a Unicode TTF or OTF font for non-ASCII text")
    align = edit.get("align", "center")
    valign = edit.get("valign", "middle")
    leading = edit.get("leading", 1.2)
    bold = edit.get("bold", False)
    italic = edit.get("italic", False)
    if align not in ("left", "center", "right") or valign not in ("top", "middle", "bottom"):
        raise HTTPException(400, "Invalid text alignment")
    if type(leading) not in (int, float) or not isfinite(leading) or not 1 <= leading <= 2:
        raise HTTPException(400, "Invalid line spacing")
    if type(bold) is not bool or type(italic) is not bool:
        raise HTTPException(400, "Invalid font style")
    if font_data and (bold or italic) and any(ord(char) > 126 for char in text):
        raise HTTPException(400, "Selected Unicode font does not support Bold or Italic")
    fontname = "hebi" if bold and italic else "hebo" if bold else "heit" if italic else "helv"
    if font_data and not (bold or italic) and (font_for_ascii or any(ord(char) > 126 for char in text)):
        try:
            fontname = "userfont"
            page.insert_font(fontname=fontname, fontbuffer=font_data)
        except Exception as exc:
            raise HTTPException(400, "Invalid Unicode font") from exc
        if any(not font_metrics.has_glyph(ord(char)) for char in text if char != "\n"):
            raise HTTPException(400, "Selected font does not contain every requested character")
    rgb = tuple(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    if edit.get("w") is not None or edit.get("h") is not None:
        w, h = edit.get("w"), edit.get("h")
        x, y = edit["x"], edit["y"]
        if not all(type(v) in (int, float) and isfinite(v) and 0 < v <= 1 for v in (w, h)) or x + w > 1.000001 or y - h < -0.000001:
            raise HTTPException(400, "Invalid text box dimensions")
        visual = fitz.Rect(x * page.rect.width, (y - h) * page.rect.height, (x + w) * page.rect.width, y * page.rect.height)
        rect = visual * page.derotation_matrix
        layout = page.new_shape()
        alignment = {"left": fitz.TEXT_ALIGN_LEFT, "center": fitz.TEXT_ALIGN_CENTER, "right": fitz.TEXT_ALIGN_RIGHT}[align]
        rotation = page.rotation
        metrics = font_metrics if font_metrics else fitz.Font(fontname=fontname)
        fitted_text = _wrap_content_text(text, max(1, visual.width - 1), metrics, size)
        available = layout.insert_textbox(rect, fitted_text, fontsize=size, fontname=fontname, color=rgb, align=alignment, lineheight=leading, rotate=rotation)
        if available < 0:
            raise HTTPException(400, "Text does not fit in the selected box. Enlarge the box or reduce the font size.")
        offset = available if valign == "bottom" else available / 2 if valign == "middle" else 0
        positioned = (fitz.Rect(visual.x0, visual.y0 + offset, visual.x1, visual.y1)) * page.derotation_matrix
        result = page.insert_textbox(positioned, fitted_text, fontsize=size, fontname=fontname, color=rgb, align=alignment, lineheight=leading, rotate=rotation, overlay=True)
        if result < 0:
            raise HTTPException(400, "Text does not fit in the selected box. Enlarge the box or reduce the font size.")
    else:
        point = fitz.Point(page.rect.width * edit["x"], page.rect.height * edit["y"]) * page.derotation_matrix
        page.insert_text(point, text, fontsize=size, fontname=fontname, color=rgb, rotate=page.rotation, overlay=True)
