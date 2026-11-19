# AGENTS.md — PDF Toolkit

## Purpose and priorities

PDF Toolkit v1.0.0 is a local-first, self-hosted PDF processing and editing application. Preserve PDF output correctness, existing API contracts, user documents, the loopback default, and the enforced CSP. The [GitHub repository](https://github.com/glitter-node/pdf-toolkit) exists but is empty as of this documentation update; no GitHub release has been verified. Read [README.md](README.md) and the relevant source before changing or documenting behavior. Explicit user instructions take priority over this file.

## Technology stack and repository map

- `app/main.py`: FastAPI entry point `app.main:app`, `/`, `/healthz`, local `/docs` and `/redoc`, static mount and site-asset routes.
- `app/core/version.py`: source version used by FastAPI/OpenAPI and the UI badge.
- `app/core/config.py`: Pydantic settings from environment variables and optional `.env`; default host and port settings are `127.0.0.1` and `8013`, but Uvicorn CLI binding must be explicit.
- `app/core/security.py`: PDF extension, signature and per-file size checks.
- `app/core/fonts.py`: allowlisted project font selection, validation and cached loading.
- `app/assets/fonts/`: Noto Sans KR and Noto Serif KR with SIL OFL 1.1 notices; the Nanum Gothic fixture and license in `tests/fixtures/` are reused.
- `app/core/limits.py`: process-local `PdfConcurrencyLimit` for `/api/pdf/`.
- `app/core/headers.py`: enforced CSP, other HTTP security headers and cache policy.
- `app/routers/pdf.py`: PDF tools, Page editor and Content editor multipart API routes.
- `app/services/pdf.py`: in-memory PDF processing, rendering, redaction and export.
- `app/templates/`: Jinja2 main page and read-only local OpenAPI viewers.
- `app/static/css/`, `app/static/js/`, `app/static/locales/`: external styles, vanilla JavaScript and four JSON locale catalogs.
- `tests/`: Python and Node regression suites; `tests/fixtures/` contains a Korean test font under its own license.
- [Windows Auto-Start](docs/WINDOWS_AUTOSTART.md): optional current-user Task Scheduler instructions, not a bundled startup script.
- `LICENSE`: MIT License for PDF Toolkit's own source code.
- `THIRD_PARTY_LICENSES.md`: separation of dependency and bundled-font licensing notices.

Use Python, FastAPI, Uvicorn, Jinja2 and vanilla JavaScript. `requirements.txt` is the package list; no external PDF executable or database is required by the current app. The current Linux environment runs Python 3.11.10, but no `requires-python` minimum or cross-platform verification matrix is declared.

## Installation and environment guidance

Run from the project root with a venv and `python -m uvicorn app.main:app --host 127.0.0.1 --port 8013`. `--reload` is for local development only, not routine operation. Linux, Windows and macOS instructions are in the [README](README.md#install-and-run); native Windows/macOS installation remains unverified in this documentation task. Keep `.env`, venvs, user documents and operational settings intact. Do not add Docker, a database, CDN, proxy or other service without an actual need and authorization.

## Development conventions and API compatibility

- Preserve existing request and response formats and route paths. Page editor uses `/api/pdf/info`, `/api/pdf/thumbnail` and `/api/pdf/organize`; Content editor uses `/api/pdf/content-edit`.
- Keep the initial HTML language `lang="ko"` under the current Korean-default UI policy; language changes update the document language. Keep CSS and JavaScript in separate files. Do not add inline style, inline script, HTML event handlers or source-code comments.
- Use English for source identifiers and developer logs. Put user-facing interface strings in the existing locale JSON files, with identical keys for all four languages. Do not inject translations or filenames as HTML.
- Keep existing API identifiers and PDF data separate from translated labels. Avoid unnecessary dependencies and browser frameworks.
- Change tests and documentation with behavior changes. Do not remove or weaken regression checks to make a change appear to pass.

The historical v0.3.0 rule remains: keep HTML, CSS and JavaScript separate and preserve API contracts. The earlier `lang="en"` guidance has been superseded by the explicit Korean-default `lang="ko"` policy in this project.

## PDF processing and editing

Protect upload validation, merge/split, extraction, page rotation/deletion/reordering, previews, Unicode text and font embedding, image insertion/movement/rotation, rectangular redaction/replacement, Undo/Redo and PDF export. Avoid changing PDF page content or overwriting originals during tests. Screen coordinates and PDF coordinates differ; changes to zoom, CropBox, page rotation, text metrics or dragging require focused regression tests and saved-PDF inspection. The browser preview does not replace validation of the exported PDF.

## Runtime limits and data preservation

`app/core/config.py` defaults to a 30 MB per-PDF upload limit, 10 merge inputs, 500 PDF pages and two simultaneous PDF API requests per process (`MAX_CONCURRENT_PDF_REQUESTS`, allowed 1–16). Other route-specific font, image and rendered-pixel checks also apply. These are not a CPU, memory or time sandbox. Keep the limits unless a tested change is requested. The app processes upload and result bytes in memory and does not configure a persistent upload directory. Preserve `.env`, venvs, operating PDF files and backups; do not automatically clear or migrate user data.

## Frontend, i18n and themes

Content editor and Unicode watermark default to the bundled Noto Sans KR font. The menu also offers Noto Serif KR, Nanum Gothic and upload. Missing bundled fonts are errors, and upload files remain limited to 10 MB. Keep font assets and license notices inside the project. Preserve Light, Dark and Warm themes and `ko`, `en`, `ja`, `zh-CN` locales, with Korean as the default. Translation JSON lives under `app/static/locales/`. `preferences.js` stores theme and language in browser localStorage. All user-visible strings, including dynamic status and accessibility labels, should follow the shared i18n API. Language and theme changes must preserve current PDF, page, editor data and Undo/Redo history. Do not recolor PDF canvases or output images through theme filters. See [UI design system](docs/UI_DESIGN_SYSTEM.md).

## Security and CSP

Keep the enforced CSP and same-origin static assets in `app/core/headers.py`; do not add `unsafe-inline`, `unsafe-eval`, arbitrary external origins or a proxy workaround for blocked code. Preserve MIME, frame, referrer, permissions, COOP/CORP and cache headers. `app/core/security.py` checks PDF extension, signature and size; PDF services validate page counts and content. The API has no built-in user authentication or rate limiting. A public path requires an approved access policy, TLS, proxy request-size/rate/time limits and process resource isolation. DSM Reverse Proxy owns HTTPS termination and HSTS; the app owns application CSP and response policy. Do not add a public deployment path without authentication and resource isolation.

## Verification restrictions

Read-only source inspection, documentation checks and tests using generated fixtures are allowed. Run `python -m pytest -q` after source changes; for other changes run relevant tests and accurately state what was and was not executed. Existing JavaScript tests use `node --test tests/*.test.cjs`; inspect `tests/` before invoking browser automation. Do not run tests against real user PDFs or drive write operations on the public service. Do not claim browser, Windows, macOS or Acrobat validation when it has not occurred.

For routine documentation work, do not restart the operating server, change DSM/Nginx/system service settings, delete user data, install packages without authorization, or deploy. Tests and link checks do not authorize publishing or operational changes.

## Documentation maintenance and reporting

Keep [README.md](README.md), [Windows Auto-Start](docs/WINDOWS_AUTOSTART.md), [UI design system](docs/UI_DESIGN_SYSTEM.md), `.env.example` and `CHANGELOG.md` aligned with the implementation. Use the actual source for settings, API fields, route behavior and limitations. Keep historical release and validation records intact. Report changed files, test commands, failures, skipped checks and deployment state separately.

PDF Toolkit's own source code is licensed under the MIT License in the root `LICENSE` file. Keep that file and its copyright notice intact. Do not describe third-party libraries, fonts, images, icons, or other assets as MIT unless their own license says so. Preserve required copyright and license notices, and review the applicable terms before adding or redistributing an asset. See [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md). A license change requires explicit approval.

## GitHub and release restrictions

The target repository is `https://github.com/glitter-node/pdf-toolkit`; it was empty when checked for this documentation update. Do not assume a tag, Release, or asset URL exists. The project source license is the root MIT `LICENSE`; do not infer that dependencies or fonts use MIT. Without explicit authorization, do not run `git init`, add/change a remote, commit, push, force-push, create/change tags or Releases, upload assets, restart the service, or deploy. Local documentation preparation is separate from publication. The test font's Open Font License does not license the project source.
