from threading import Lock


class PdfConcurrencyLimit:
    def __init__(self, app, limit: int):
        self.app = app
        self.limit = limit
        self.active = 0
        self.lock = Lock()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith("/api/pdf/"):
            await self.app(scope, receive, send)
            return
        with self.lock:
            admitted = self.active < self.limit
            if admitted:
                self.active += 1
        if not admitted:
            body = b'{"detail":"Too many PDF requests. Try again shortly."}'
            await send({"type": "http.response.start", "status": 429, "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode()), (b"cache-control", b"no-store")]})
            await send({"type": "http.response.body", "body": body})
            return
        try:
            await self.app(scope, receive, send)
        finally:
            with self.lock:
                self.active -= 1
