from fastapi import HTTPException, UploadFile
from app.core.config import settings


async def read_pdf(upload: UploadFile) -> bytes:
    if not upload.filename or not upload.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")
    limit = settings.max_upload_mb * 1024 * 1024
    data = await upload.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, "File size limit exceeded")
    if not data.startswith(b"%PDF-"):
        raise HTTPException(400, "Invalid PDF file")
    return data
