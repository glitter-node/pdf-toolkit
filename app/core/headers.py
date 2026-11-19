CONTENT_SECURITY_POLICY = "; ".join((
    "default-src 'none'",
    "base-uri 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "form-action 'self'",
    "script-src 'self'",
    "script-src-attr 'none'",
    "style-src 'self'",
    "style-src-elem 'self'",
    "style-src-attr 'none'",
    "font-src 'self' blob:",
    "connect-src 'self'",
    "img-src 'self' blob:",
    "media-src 'none'",
    "worker-src 'none'",
    "manifest-src 'self'",
))
SECURE_CONTENT_SECURITY_POLICY = CONTENT_SECURITY_POLICY + "; upgrade-insecure-requests"


class SecurityHeaders:
    def __init__(self, app):
        self.app = app

    def headers_for(self, path, current, secure=False):
        names = {
            b"content-security-policy": (SECURE_CONTENT_SECURITY_POLICY if secure else CONTENT_SECURITY_POLICY).encode(),
            b"x-content-type-options": b"nosniff",
            b"referrer-policy": b"strict-origin-when-cross-origin",
            b"x-frame-options": b"DENY",
            b"permissions-policy": b"camera=(), microphone=(), geolocation=(), payment=(), usb=()",
            b"cross-origin-opener-policy": b"same-origin",
            b"cross-origin-resource-policy": b"same-origin",
        }
        if path.startswith("/static/") or path in ("/favicon.ico", "/robots.txt", "/sitemap.xml"):
            cache = b"public, max-age=3600"
        else:
            cache = b"no-store"
        names[b"cache-control"] = cache
        filtered = [(key, value) for key, value in current if key.lower() not in names and key.lower() != b"content-security-policy-report-only"]
        return filtered + list(names.items())

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        secure = any(key == b"x-forwarded-proto" and value.lower() == b"https" for key, value in scope.get("headers", []))
        started = False

        async def secured_send(message):
            nonlocal started
            if message["type"] == "http.response.start":
                message = dict(message)
                message["headers"] = self.headers_for(path, message.get("headers", []), secure)
                started = True
            await send(message)

        try:
            await self.app(scope, receive, secured_send)
        except Exception:
            if started:
                raise
            body = b'{"detail":"Internal server error"}'
            await secured_send({"type": "http.response.start", "status": 500, "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
            await secured_send({"type": "http.response.body", "body": body})
