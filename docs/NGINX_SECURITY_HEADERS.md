# Nginx header ownership and rollout example

## Read-only findings

The active reverse proxy file is `/usr/local/etc/nginx/sites-enabled/server.ReverseProxy.conf`. Its `pdf-toolkit.glitter.kr` HTTPS server proxies `/` to `127.0.0.1:8013` and has no host-specific CSP, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy, COOP, or CORP directive. `nginx -T` exited successfully. The global included file `/var/tmp/nginx/trusted_proxy/z_htp_map_geo.conf` declares `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`; HTTPS responses showed one such header. HTTP `/healthz` returned 301 to HTTPS with that HSTS header. The observed HTTPS HTML, health, static, and 405 API responses had no CSP or other listed security headers before RC3. The direct loopback production app also had none. This is a read-only observation of v0.16.0, not a post-RC3 proxy result.

## Responsibility split

Nginx retains HTTPS, HSTS, the approved public access policy, request size, rate and connection limits, and worker isolation. FastAPI owns the single Report-Only CSP and the content-specific headers listed in `RC3_SECURITY_AUDIT.md`. Do not add the same CSP, XFO, nosniff, Referrer, or Permissions headers again in Nginx. Multiple CSP headers are independently enforced by browsers; they do not merge into a single permissive policy.

No Nginx change is required for RC3's application headers. If an approved future change adds a location-level `add_header`, account for Nginx inheritance: a location-level `add_header` can replace inherited headers, including the current global HSTS. Review the complete effective server block and ensure exactly one HSTS result before reloading. The following is a review example only, showing the current division of responsibility rather than an instruction to append directives:

```nginx
server {
    listen 443 ssl;
    server_name pdf-toolkit.glitter.kr;
    location / {
        proxy_pass http://127.0.0.1:8013;
    }
}
```

The approved authentication and PDF resource policy must be supplied separately; this example is not a deployable public configuration.

## Validation and rollback

Before any approved Nginx change, back up the exact generated configuration and its active symlink, record its hash, and identify the service manager. Inspect with `nginx -T` and validate with `nginx -t`; do not assume a reload command. After an approved change, compare `curl -sS -D - -o /dev/null https://pdf-toolkit.glitter.kr/`, `/healthz`, `/static/js/app.js`, and a 4xx API response. Count each relevant header and compare direct loopback versus proxy responses. Use `curl -sS -D - -o /dev/null http://pdf-toolkit.glitter.kr/healthz` to confirm the HTTP redirect. If any required header disappears, duplicate CSP appears, or the app fails, restore the backed-up file and use the verified service procedure to reload only Nginx. No Nginx configuration or process was changed for RC3.
