# RC3 security audit

## Resource inventory

The Content editor uses local JavaScript and CSS and the server-rendered PNG preview on the same origin. The project contains no PDF.js or browser Worker. The original app HTML had no external script, CSS, or font URL. FastAPI's automatic `/docs` page did load Swagger UI JavaScript and CSS from jsDelivr and a FastAPI favicon; `/redoc` loaded ReDoc from jsDelivr, Google Fonts, and the FastAPI favicon. Both default docs pages included or depended on inline execution. RC3 disables those default pages while preserving `/docs`, `/redoc`, and `/openapi.json` paths with a local read-only schema viewer. The schema viewer does not offer Swagger UI's interactive request form.

| Item | Finding and classification | RC3 action |
| --- | --- | --- |
| External CDN scripts, CSS, fonts | Present in FastAPI default docs; removable | Replaced with local docs.js and docs.css; no bundled third-party runtime remains |
| HTML inline script, style, event attributes | None in app templates; default docs had inline initialization | Custom docs templates use external local files |
| eval, new Function, string timers, dynamic scripts, document.write, javascript: URLs | None in application JS | Regression scan added; inspected Swagger UI and ReDoc bundles were rejected because both contained new Function and ReDoc generated styles |
| iframe, dynamic import, Worker | None in application JS | worker-src remains self only |
| innerHTML, insertAdjacentHTML | None in application JS | Docs schema values are assigned through textContent |
| blob: | Seven URL.createObjectURL sites for uploaded font preview, images, page previews, and downloads | font-src and img-src permit blob; downloads retain the existing Blob URL flow |
| data: | No application HTML, CSS, or JS resource needs it | No data: allowance in the policy |
| External URLs | Canonical URL, robots sitemap, sitemap XML metadata only | No browser resource fetch or API call to an external origin |
| CSS URL and @import | None in app CSS | No external style or font request |

The temporary evaluation of `swagger-ui-dist` 5.29.5 and `redoc` 2.5.2 verified npm tarball SHA-512 integrity and Apache-2.0/MIT license metadata, but the bundles were removed from RC3 before packaging. No vendor asset is distributed. The final CSS and JavaScript are written in the project and loaded from `/static/`.

## Enforced CSP

```text
default-src 'none'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; script-src 'self'; script-src-attr 'none'; style-src 'self'; style-src-elem 'self'; style-src-attr 'none'; font-src 'self' blob:; connect-src 'self'; img-src 'self' blob:; media-src 'none'; worker-src 'none'; manifest-src 'self'
```

The only source exception is `blob:` for uploaded font preview and image/page preview. No `unsafe-inline`, `unsafe-eval`, wildcard, blanket `https:`, or `data:` appears. HTTPS requests identified by DSM's `X-Forwarded-Proto: https` additionally receive `upgrade-insecure-requests`; direct loopback HTTP does not, preserving the documented binding. The policy is now enforced as `Content-Security-Policy`. Browser E2E remains unavailable on this host, so enforcement compatibility is not claimed as a Lighthouse or Chrome result.

## Application response headers

| Header | RC3 application behavior |
| --- | --- |
| Content-Security-Policy | Single enforced strict policy on HTTP responses |
| X-Content-Type-Options | nosniff |
| Referrer-Policy | strict-origin-when-cross-origin |
| X-Frame-Options | DENY |
| Permissions-Policy | Camera, microphone, geolocation, payment, USB disabled |
| Cache-Control | no-store for HTML, API, health, errors, downloads; public max-age=3600 for `/static/`, favicon, robots, sitemap |
| Strict-Transport-Security | Not sent by FastAPI; HTTPS edge owns HSTS |
| Cross-Origin-Opener-Policy, Cross-Origin-Resource-Policy | Deferred until browser checks of previews, uploads, and Blob downloads |
| Access-Control-Allow-Origin | Not sent; the app fetches its own origin only |

The existing download helper keeps fixed `Content-Disposition`, no-store, and nosniff values. Middleware replaces duplicate app-owned headers with one value and catches unhandled exceptions before response start with a generic JSON 500 body. Tests cover 200, 400, 405 OPTIONS, 422, 500, static files, previews, downloads, and absence of server paths. Streaming errors after response start cannot be rewritten into a new response.

## Remaining High risk

The public access policy remains undefined. The current public proxy has no confirmed authentication, PDF-specific rate or connection limits, body size limit, or isolated CPU, memory, and hard processing-time controls. RC2's per-process concurrency limit does not replace OS resource isolation. CSP and HTTP headers do not resolve this risk. The RC3 source was applied to the existing operating path by explicit instruction on 2026-11-19; the security release gate remains failed.
