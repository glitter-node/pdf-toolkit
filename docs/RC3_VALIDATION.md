# RC3 validation record

RC3 was copied from the RC2 staging source. Before source application, production was v0.16.0 at `127.0.0.1:8013`. The RC3 source was applied to the same operating path on 2026-11-19 by explicit instruction. The existing `.env`, virtual environment, Nginx configuration, and service launch command were preserved.

## Commands and results

| Command | Result |
| --- | --- |
| `/volume1/glitter/pdf-toolkit/venv/bin/python -m pytest -q` | 139 passed, 0 failed, 0 skipped, 5 upstream PyMuPDF warnings |
| `node --test tests/*.test.cjs` | 33 passed, 0 failed |
| `/volume1/glitter/pdf-toolkit/venv/bin/python -m compileall -q app tests` | Passed |
| `node --check` for all five app JavaScript files | Passed |
| `/volume1/glitter/pdf-toolkit/venv/bin/python -m pip check` | Passed |
| `PLAYWRIGHT_NODEJS_PATH=/usr/local/bin/node /volume1/glitter/pdf-toolkit/venv/bin/python -m pytest -q -x tests/e2e_rc2.py` | Browser setup error; `libatk-1.0.so.0` missing; 0 scenarios and 0 viewport checks executed |

The browser error is stored in `artifacts/e2e/browser-launch-error.txt`. A screenshot is unavailable before Chromium starts. The existing Dockerfile E2E setup can run the suite on a supported separate machine. The browser CSP console check was added but has not run. Static and DOM tests do not count as browser compatibility verification.

## Scope and limitations

The nine RC3 Python security tests cover the main HTML, API success and errors, 405 OPTIONS, 422 validation, generic 500, static and metadata caching, local docs resources, CSP policy shape and count, preview PNG, and edited PDF download integrity with PyMuPDF and pypdf. The two new Node tests verify local schema rendering through text nodes and safe error text. Existing PDF tools, Page editor, Content editor, Unicode font, rotation, CropBox, redaction, and PDF integrity tests remain active.

The CSP is enforced as `Content-Security-Policy`; `Content-Security-Policy-Report-Only` is absent. COOP and CORP are also present. `/docs` and `/redoc` are local read-only OpenAPI schema pages instead of interactive Swagger UI and ReDoc. API routes and request/response formats remain unchanged. Acrobat was not run. Browser E2E remains blocked, and the public access and resource isolation High risk remains. Source application does not mean the release gate passed.

The immediate pre-application rollback backup is `/volume1/glitter/pdf-toolkit-pre-rc3-20261119T041755Z`; its 48-file SHA-256 manifest was verified. The older v0.16.0 backup remains at `/volume1/glitter/pdf-toolkit-v0160-backup-20261119T034102Z`. No rollback was required.

## Operating source application and post-application checks

The RC3 archive was extracted and checked outside the operating path. Twenty-seven changed archive files were atomically applied, including 17 new files. `.env` matched its backup hash afterward. No service launch or restart command was issued. The existing service reported `/healthz` 200 and OpenAPI version `0.17.0` on loopback and through the public proxy. The public HTML, docs, API schema, and static assets returned 200 with one enforced CSP, no Report-Only CSP, and one Nginx HSTS header.

A real loopback HTTP smoke check posted a generated two-page PDF to `/api/pdf/info`, `/api/pdf/render`, and `/api/pdf/content-edit` with a Korean test font. All returned 200. The saved PDF reopened with PyMuPDF and pypdf, retained two pages, contained the mixed Korean/English edit, preserved the untouched page, and left the source bytes unchanged. The operating path passed 139 Python tests, 33 JavaScript tests, Python compileall, five JavaScript syntax checks, and pip check. Chromium E2E remained blocked by the missing `libatk-1.0.so.0` library. Public authentication, rate/body controls, and CPU/memory/time isolation remain unresolved High risk.
