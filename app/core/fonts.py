from functools import lru_cache
from pathlib import Path

import fitz
from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[2]
FONTS = {
    "default": ("Noto Sans KR", ROOT / "app/assets/fonts/NotoSansKR.ttf"),
    "noto-serif-kr": ("Noto Serif KR", ROOT / "app/assets/fonts/NotoSerifKR.ttf"),
    "nanum-gothic": ("Nanum Gothic", ROOT / "tests/fixtures/NanumGothic-Regular.ttf"),
}


def bundled_font(font_id: str) -> bytes:
    if font_id not in FONTS:
        raise HTTPException(400, "Unknown font identifier")
    path = FONTS[font_id][1]
    try:
        parts = path.relative_to(ROOT).parts
    except ValueError as exc:
        raise HTTPException(503, f"Bundled font unavailable: {font_id}") from exc
    if any((ROOT.joinpath(*parts[:index])).is_symlink() for index in range(1, len(parts) + 1)) or not path.is_file():
        raise HTTPException(503, f"Bundled font unavailable: {font_id}")
    try:
        stat = path.stat()
        return _read_font(font_id, stat.st_mtime_ns, stat.st_size)
    except (OSError, ValueError, RuntimeError) as exc:
        raise HTTPException(503, f"Bundled font unavailable: {font_id}") from exc


@lru_cache(maxsize=3)
def _read_font(font_id: str, mtime_ns: int, size: int) -> bytes:
    data = FONTS[font_id][1].read_bytes()
    if not data or len(data) > 30_000_000:
        raise ValueError("Invalid bundled font size")
    font = fitz.Font(fontbuffer=data)
    if not all(font.has_glyph(ord(char)) for char in "한글 A"):
        raise ValueError("Missing required glyphs")
    return data


def available_fonts() -> list[dict[str, str]]:
    result = []
    for font_id, (name, _) in FONTS.items():
        try:
            bundled_font(font_id)
        except HTTPException:
            continue
        result.append({"id": font_id, "name": name})
    return result


def select_font(font_id: str | None, uploaded: bytes | None) -> bytes:
    if font_id is None and uploaded is not None:
        return uploaded
    if font_id == "upload":
        if uploaded is None:
            raise HTTPException(400, "Upload mode requires a font file")
        return uploaded
    if uploaded is not None:
        raise HTTPException(400, "Uploaded font conflicts with selected bundled font")
    return bundled_font("default" if font_id is None else font_id)
