# PDF Toolkit

**PDF Toolkit v1.0.0 — Initial Public Release source**

PDF Toolkit is a local-first, self-hosted PDF processing and editing toolkit built with Python, FastAPI, Uvicorn, Jinja2, and vanilla JavaScript. The same application serves local development and normal operation. PDF processing runs on the host; the browser preview does not prove that an exported PDF renders identically in every reader. Local use requires no database, Docker, Nginx, Apache, or external conversion service.

The [planned GitHub repository](https://github.com/glitter-node/pdf-toolkit) currently exists but is empty. No release tag or GitHub download asset has been verified. This document describes the local 1.0.0 source, not a completed GitHub publication or a verified deployment on every platform.

## Project links

- [Repository — planned publication; currently empty](https://github.com/glitter-node/pdf-toolkit)
- Release — not published; no release download URL is available
- [README](README.md)
- [Windows Auto-Start](docs/WINDOWS_AUTOSTART.md)
- [Agent instructions](AGENTS.md)
- [UI design system](docs/UI_DESIGN_SYSTEM.md)
- [License](LICENSE) — PDF Toolkit source code is licensed under the MIT License
- [Third-party licenses](THIRD_PARTY_LICENSES.md) — dependency and bundled-font notices

## Choose a workflow

1. **PDF tools:** choose one of 11 operations, upload documents, set options, process, and download the result.
2. **Page editor:** inspect thumbnails, reorder, select, rotate or delete pages, undo an edit, and export a new PDF.
3. **Content editor:** preview pages, add or edit text and images, remove or replace a rectangular region, undo or redo, and export a new PDF.

The browser sends selected PDFs to FastAPI for processing. Uploads are not intentionally persisted by the app; the generated result is returned as an in-memory HTTP response and downloaded by the browser.

## Features

| Workflow | Implemented operations |
| --- | --- |
| PDF tools | Merge; extract pages; split into individual or grouped PDFs in a ZIP; rotate; render PNG/JPEG; optimize content streams; add ASCII, Unicode-font or image watermarks; AES-256 password protection; extract selectable text to UTF-8 TXT |
| Page editor | PDF information and thumbnails; selection, reorder, rotate, delete, Undo, and export |
| Content editor | Unicode text with bundled or uploaded TTF/OTF font; text alignment, wrapping, movement and resizing; PNG/JPEG insertion, movement, resizing and rotation; rectangular redaction/replacement; Undo/Redo and export |

Page ranges use `1,3-5` notation. The split API supports `single` and `ranges` modes. Redaction removes content in the chosen rectangle and can affect nearby material; inspect the exported copy. Text extraction does not perform OCR. The source PDF file is not overwritten.

## Technology stack and requirements

| Part | Current implementation |
| --- | --- |
| Backend | Python, FastAPI, Uvicorn, Jinja2, Pydantic settings |
| PDF processing | PyMuPDF, pypdf, ReportLab, Pillow, cryptography |
| Frontend | External CSS, vanilla JavaScript, JSON locale catalogs |
| Static assets | Same-origin `/static/` CSS, JavaScript and locale JSON |
| Runtime storage | PDF input and output bytes in memory; downloads on the client |
| Database | None required |
| Python compatibility | No declared `requires-python` minimum; current Linux environment uses Python 3.11.10 |
| Browser | Modern browser with JavaScript, Canvas, file input and Blob downloads; no completed cross-browser matrix |

Python package constraints are in [requirements.txt](requirements.txt). Node.js is needed for JavaScript tests, not to run the app. The licensed Nanum Gothic file in `tests/fixtures/` is also an available runtime font; it is reused without copying the binary.

| Platform | Guidance | Verification in this documentation task |
| --- | --- | --- |
| Linux | Create a venv and install `requirements.txt` | Existing Linux Python 3.11 environment inspected; fresh installation not run |
| Windows 10/11 | PowerShell with Python 3.11 venv | Native installation and Task Scheduler not run |
| macOS Intel | Intel-compatible Python and package wheels | Not run |
| macOS Apple Silicon | Native arm64 Python and matching package wheels | Not run |

## Install and run

Use the directory containing `app/main.py`, `requirements.txt` and `.env.example`. For a new installation, copy `.env.example` only if settings are needed. Preserve any existing `.env` or virtual environment. Settings default to `127.0.0.1:8013`, but Uvicorn CLI binding needs explicit arguments.

### Linux

```bash
cd /path/to/pdf-toolkit
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8013
```

### Windows 10/11 PowerShell

```powershell
Set-Location (Read-Host "Enter the full path to the PDF Toolkit project")
py --list
py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8013
```

Use an installed Python 3.11 interpreter if `py -3.11` is unavailable. Calling `python.exe` directly avoids changing PowerShell execution policy. See [Windows Auto-Start](docs/WINDOWS_AUTOSTART.md).

### macOS Intel

```bash
cd /path/to/pdf-toolkit
uname -m
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8013
```

### macOS Apple Silicon

```bash
cd /path/to/pdf-toolkit
uname -m
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8013
```

Match the interpreter and wheels to the Mac architecture. These are source-based instructions; native Windows and macOS installation was not performed here. Open `http://127.0.0.1:8013/` on the same computer. Ctrl+C stops a foreground process. `--reload` is optional during development only. Normal operation omits it.

## Configuration

`app/core/config.py` reads environment variables and optional `.env` from the working directory. The app starts without `.env`. [`.env.example`](.env.example) lists the current settings. Neither host nor port settings automatically change Uvicorn CLI binding.

| Variable | Source default | Purpose | Required? | Security consideration |
| --- | --- | --- | --- | --- |
| `APP_HOST` | `127.0.0.1` | Reference bind host | No | Keep loopback for local use |
| `APP_PORT` | `8013` | Reference port | No | Check ownership before starting |
| `MAX_UPLOAD_MB` | `30` | Per-PDF upload size limit | No | Does not replace proxy body-size limits |
| `MAX_FILES` | `10` | Maximum PDFs in a merge request | No | Other endpoints have separate checks |
| `MAX_PAGES` | `500` | Maximum PDF page count | No | Parsing can still consume substantial resources |
| `MAX_CONCURRENT_PDF_REQUESTS` | `2` per process | Simultaneous `/api/pdf/` requests; valid 1–16 | No | Multiple workers need separate external isolation |

No database or persistent upload directory is configured. Do not publish `.env` or secrets.

## Application routes and processing workflow

| Route | Method | Purpose and result |
| --- | --- | --- |
| `/` | GET | Main application HTML |
| `/healthz` | GET | `{"status":"ok"}`; process health only |
| `/docs`, `/redoc` | GET | Local read-only OpenAPI viewers |
| `/openapi.json` | GET | OpenAPI schema and source version |
| `/static/{path}` | GET | CSS, JavaScript, locale JSON and other assets |
| `/favicon.ico`, `/robots.txt`, `/sitemap.xml` | GET | Site assets and metadata |
| `/api/pdf/merge` | POST | `files` (2 to `MAX_FILES`) → PDF |
| `/api/pdf/extract` | POST | `file`, `pages` → PDF |
| `/api/pdf/split` | POST | `file`, optional `pages`, `mode` → ZIP |
| `/api/pdf/rotate` | POST | `file`, `angle`, optional `pages` → PDF |
| `/api/pdf/render` | POST | `file`, `page`, `image_format`, `dpi` → PNG or JPEG |
| `/api/pdf/compress` | POST | `file` → optimized PDF, not guaranteed smaller |
| `/api/pdf/watermark` | POST | `file`, ASCII `text`, options → PDF |
| `/api/pdf/protect` | POST | `file`, `password` → AES-256 PDF |
| `/api/pdf/text` | POST | `file`, optional `pages` → UTF-8 TXT |
| `/api/pdf/unicode-watermark` | POST | `file`, `text`, optional `font_id` or `font`, options → PDF |
| `/api/pdf/image-watermark` | POST | `file`, `image`, options → PDF |
| `/api/pdf/info` | POST | `file` → page count and dimensions JSON |
| `/api/pdf/thumbnail` | POST | `file`, `page` → PNG |
| `/api/pdf/organize` | POST | `file`, JSON `operations` → PDF |
| `/api/pdf/content-edit` | POST | `file`, JSON `edits`, optional `font_id`, `font` and `images` → PDF |

PDF endpoints use multipart form fields. Downloads have server-chosen filenames and `Content-Disposition: attachment`. `/info` returns JSON and `/thumbnail` returns an image. See `/openapi.json` for the exact schema and [app/routers/pdf.py](app/routers/pdf.py) for details.


### Bundled Unicode fonts

The Content editor and Unicode watermark use the project's Noto Sans KR font automatically. Select Noto Serif KR or Nanum Gothic in the font menu, or choose upload and provide a TTF/OTF file under 10 MB. The selected font is embedded in exported PDFs. For compatibility, older API requests with neither `font_id` nor `font` keep the built-in PDF font for ASCII-only text; Unicode text uses Noto Sans KR. A missing or invalid bundled font produces an error; it does not silently fall back to a system font. Unsupported glyphs are rejected. The Bold/Italic controls are rejected for Unicode text because the bundled font styles do not support them. To use a styled Unicode face, upload its styled font file without those controls. ASCII Bold/Italic still uses the PDF built-in Helvetica styles. The browser canvas loads the selected font from a same-origin allowlisted route, but its layout remains approximate.

The server accepts `font_id=default`, `noto-serif-kr`, `nanum-gothic`, or `upload`. With no `font_id`, an uploaded `font` retains the older upload behavior; otherwise the default applies. Upload mode requires `font`; an upload with a different explicit selection is an error. The server never accepts a font path from the browser.

Bundled Noto Sans KR and Noto Serif KR TTF files and their SIL Open Font License 1.1 notices are in `app/assets/fonts/`, sourced from the official [Noto Sans KR](https://github.com/google/fonts/tree/main/ofl/notosanskr) and [Noto Serif KR](https://github.com/google/fonts/tree/main/ofl/notoserifkr) directories in Google's font repository. The existing Nanum Gothic TTF in `tests/fixtures/` is reused, with its own OFL notice there. Do not remove or separate these notices when redistributing fonts. Font licenses cover the fonts, not the application source. The Noto files are variable fonts; this PyMuPDF version selects their Thin and ExtraLight default instances. To replace a font, put a licensed TTF/OTF and its notice inside the project, update the allowlist in `app/core/fonts.py`, and verify PDF extraction and embedded font metadata. Do not configure a system font path.

## Operations and security

The server checks PDF filename extension, `%PDF-` signature, size and page count; rejects encrypted or malformed PDFs; constrains rendered image dimensions; and limits simultaneous PDF API requests per process with HTTP 429 on saturation. Font and image uploads have separate route checks. These controls do not sandbox CPU, memory, or processing time. Crafted PDFs can still consume significant resources.

The app does not implement user authentication or rate limiting. Do not expose Uvicorn directly to the internet. A deliberate public deployment needs an approved access policy, TLS, proxy request-size and rate controls, timeouts, and process-level resource isolation. The public URL `https://pdf-toolkit.glitter.kr` is a separate DSM Reverse Proxy deployment; the local commands use `http://127.0.0.1:8013` and do not configure that proxy. Protect uploaded documents and downloaded results.

## Security headers and CSP

`app/core/headers.py` supplies an enforced same-origin CSP, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, Permissions Policy, COOP and CORP `same-origin`, and path-specific Cache-Control. It does not allow `unsafe-inline` or `unsafe-eval`. The policy allows same-origin scripts, styles and connections, plus `blob:` fonts/images; forwarded HTTPS requests also receive `upgrade-insecure-requests`. Static assets have one-hour public caching; HTML and API responses use `no-store`. Report-Only CSP is not intentionally emitted by the app.

HSTS belongs to DSM's HTTPS termination layer, not FastAPI. Multiple CSP headers are all enforced, so inspect both layers before changing proxy headers. Check local headers with `curl -I http://127.0.0.1:8013/`, then inspect `curl -I https://pdf-toolkit.glitter.kr/` separately if authorized. See the [RC3 audit](docs/RC3_SECURITY_AUDIT.md) and [proxy guidance](docs/NGINX_SECURITY_HEADERS.md). This documentation task changes no security policy.

## Site assets and public URL

The app serves favicon, robots.txt and sitemap.xml from `app/main.py`. External CSS, JavaScript and four JSON catalogs are served from `app/static/`. The public canonical URL and sitemap refer to `https://pdf-toolkit.glitter.kr`; localhost remains the default for self-hosted operation and testing.

## Keyboard controls

In the Content editor, Delete/Backspace removes a selected edit; Ctrl/Command+Z undoes; Ctrl/Command+Y and Ctrl/Command+Shift+Z redo; arrow keys move a selected object, and Shift+arrow moves farther. Escape cancels the current selection or edit. These shortcuts avoid text inputs and dialogs. The Page editor has an Undo button and move controls; the Content editor shortcuts do not all apply there.

## Themes and languages

Themes are Light, Dark and Warm. Korean (`ko`) is the default; English (`en`), Japanese (`ja`) and Simplified Chinese (`zh-CN`) are available. `app/static/js/preferences.js` saves choices under `pdf-toolkit-theme` and `pdf-toolkit-language` in browser localStorage. Invalid choices fall back to Light and Korean. Switching themes or languages preserves editor state; themes do not recolor PDF canvas or images.

## Workspace design

The header, navigation tabs and workspace panels share layout and color tokens. Responsive toolbars support desktop, tablet and mobile; PDF preview scrolling stays inside its own container. Focus styles, live status, reduced motion and contrast rules are detailed in [UI design system](docs/UI_DESIGN_SYSTEM.md) and [accessibility audit](docs/ACCESSIBILITY_AUDIT.md). This is not a claim of completed assistive-technology testing.

## Development, verification and troubleshooting

From the project root, with a venv activated or by using its Python executable:

```bash
python -m pytest -q
python -m compileall -q app tests
python -m pip check
node --test tests/*.test.cjs
find app/static/js -type f -name '*.js' -exec node --check {} \;
```

The Korean embedding test uses `tests/fixtures/NanumGothic-Regular.ttf` under `tests/fixtures/NanumGothic-OFL.txt`. `PDF_TOOLKIT_TEST_KOREAN_FONT` can select another local TTF/OTF. For startup failure, check the working directory, interpreter, installed packages and port 8013. For PDF errors, check file type, encryption, size, pages and form fields. For preview/export differences, inspect the exported PDF. Browser automation instructions and known host library issues are in [RC2 validation](docs/RC2_VALIDATION.md).

## Known limitations and verification status

- No OCR or reconstruction of existing PDF text layout; Acrobat compatibility has not been verified in Acrobat.
- CPU, memory and time isolation, authentication, and proxy rate limits are not supplied by the FastAPI app.
- Windows/macOS installation and Task Scheduler behavior were not executed for this documentation update.
- Previous Playwright execution on this host was blocked by missing shared libraries; this documentation work is not browser E2E validation.
- The GitHub repository is empty and no release asset is published there. Source and running-service versions must be checked separately.

## License

PDF Toolkit is licensed under the MIT License. See [LICENSE](LICENSE) for details.

The MIT License applies to PDF Toolkit's own source code. Third-party libraries and bundled fonts retain their own licenses; see [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) and the license notices beside the font files. In particular, PyMuPDF's installed distribution is dual licensed under the GNU Affero GPL 3.0 or the Artifex Commercial License. The project source does not select a PyMuPDF commercial license or alter those terms.

## Development history

The existing version-specific notes below are retained. [CHANGELOG.md](CHANGELOG.md) is the release history; historical validation reports are in [docs/](docs/).

### v1.0.0 stable release preparation

The current source uses one version value in `app/core/version.py` for FastAPI, OpenAPI, and the UI badge. This version update does not change PDF processing behavior. Verify the live service version separately after a controlled restart; changing source files alone does not reload the running application. The existing security and browser validation limits remain documented below.

### v0.18.0 UI system

The interface uses shared CSS custom properties for Light, Dark, and Warm themes. Theme and language preferences are stored locally in the browser; Korean is the default language, with English, Japanese, and Simplified Chinese translations in `app/static/locales/`. Operation labels and common runtime statuses follow the selected locale without changing API identifiers. Responsive breakpoints support desktop, tablet, and mobile layouts without changing PDF canvas coordinates. All scripts and styles remain external to preserve the enforced CSP.

The four locale catalogs share an identical key set. Dynamic Page editor and Content editor labels use the common i18n API and preserve current files, pages, edits, and history when the language changes. Development and browser validation instructions are documented in `docs/I18N_ARCHITECTURE.md` and `docs/I18N_TEST_MATRIX.md`.

Theme contrast tokens and the static WCAG AA audit are documented in `docs/ACCESSIBILITY_AUDIT.md`.

Local self-hosted PDF processing powered by Python, FastAPI, and Uvicorn. No Nginx, Apache, Docker, or database is required for local use.

### Features

- Merge PDF files
- Extract selected pages using `1,3-5` notation
- Split pages into individual PDFs or grouped ranges, downloaded as a ZIP archive
- Rotate selected pages
- Render one PDF page as PNG or JPEG
- Optimize PDFs when a smaller lossless result is possible
- Add ASCII text, Unicode text with a bundled or uploaded font, or image watermarks
- Protect PDFs with an AES-256 password
- Extract selectable text to UTF-8 TXT
- Edit page order, rotation, and deletion in the Page editor, with Undo for the last 30 edits

### Install

```bash
python -m venv venv
. venv/bin/activate
python -m pip install --only-binary=pymupdf -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8013
```

Windows Git Bash: activate with `source venv/Scripts/activate`.

Open http://127.0.0.1:8013. API docs: http://127.0.0.1:8013/docs.

### Tests

```bash
python -m pytest -q
node --test tests/*.test.cjs
```

The Korean text embedding test uses the bundled Nanum Gothic Regular test fixture under its Open Font License. Set `PDF_TOOLKIT_TEST_KOREAN_FONT` to a local Korean TTF or OTF file to override it. See `tests/fixtures/NanumGothic-OFL.txt` for the license.

### v0.17.0 RC3 security headers

The app emits an enforced same-origin Content-Security-Policy with no unsafe-inline or unsafe-eval. HTTPS proxy requests also receive upgrade-insecure-requests; direct loopback HTTP remains usable. It adds MIME, referrer, frame, permissions, COOP/CORP, and path-specific cache headers. The `/docs` and `/redoc` paths display the local OpenAPI schema using the app's own JavaScript and CSS, without CDN assets or inline execution. These pages are read-only and do not include Swagger UI's interactive request form. The RC3 source was applied to the existing operating path on 2026-11-19 by explicit instruction; browser E2E and public access/resource isolation gates remain unresolved. See `docs/RC3_SECURITY_AUDIT.md`, `docs/RC3_VALIDATION.md`, and `docs/NGINX_SECURITY_HEADERS.md` for the validation limits.

### v0.17.0 RC2 validation

The render endpoint checks projected pixel dimensions before allocating a pixmap. RC2 adds a configurable per-process PDF request concurrency limit and rejects excessive image uploads before reading their content. Run the browser suite on a supported test machine using the pinned Playwright image and the instructions in `docs/RC2_VALIDATION.md`. The production deployment gate remains closed until browser verification and an approved public access policy are in place.

### v0.16.0 Content editor UX

- The text dialog adjusts its textarea rows for longer input, keeps keyboard focus inside, restores the previous focus on close, and cancels from Escape, Cancel, or a backdrop click. Enter remains available for line breaks.
- Selecting another PDF asks before discarding unsaved edits. Reloading the current PDF also asks when edits are unsaved. Page and workspace tab changes keep edits. Leaving the browser page warns only while edits differ from the last successful export.
- Save checks the loaded PDF, edit bounds, basic text fit, fonts, and image references before sending. Server text fitting and PDF validation remain authoritative. Failed saves retain edits; stale responses from a replaced file are ignored.
- Content controls have larger touch targets on small screens. The preview canvas supports pointer gestures and keyboard focus, and narrow layouts leave room for the Back to top button.

### v0.15.0 editing engine reliability

- PDF text boxes wrap long strings using the embedded or built-in font's measured width. Uploaded fonts are checked for every requested glyph; missing characters produce a validation error.
- Content editor objects have internal unique IDs that survive Undo/Redo. IDs and manual sizing state are excluded from the existing save API payload.
- Proportional image resizing can enlarge images while respecting page edges. Page changes, mode changes, and saving cancel an unfinished drag and restore its prior state.
- Automated tests cover all four page rotations with and without CropBox, redaction of original text with nearby content preserved, Unicode font embedding, and saved PDF integrity.

### v0.14.0 Content editor stabilization

- Text additions accept Unicode and line breaks. Automatic sizing measures the selected font in the browser, wraps near page boundaries, and keeps a manually resized width when text changes. PDF export still validates fit with PyMuPDF and reports an error if text cannot fit.
- Text and image edits support Delete, Undo, Redo, arrow keys, and Escape outside input fields and the text dialog. Shift with an arrow moves an item by 10 PDF points.
- Pointer cancellation restores the edit. File replacement closes the text dialog and prevents pending edits from changing the new document.
- Images added over a replacement region remain in the saved PDF. Visual coordinates are transformed for rotated pages. Export preserves other pages and leaves the source file untouched.
- Browser text preview uses browser font metrics and may differ from the PDF renderer. Inspect the exported PDF in a reader before sharing. Acrobat compatibility has not been verified in Acrobat.

### Security and scope

Files are processed in memory and not intentionally persisted by the app. PDF filename extension, signature, file size, page count, and image output dimensions are checked. Encrypted input PDFs are rejected. Text extraction requires selectable text; OCR and direct editing of PDF body text are not supported. PDF parsing is CPU/memory intensive, and this local self-hosted app has no authentication, rate limits, or isolated worker execution. Do not expose it directly to the internet. A public reverse proxy requires authentication, upload limits, timeouts, concurrency controls, and worker isolation.

### Split API

POST `/api/pdf/split` accepts `file`, optional `pages`, and `mode` (`single` or `ranges`). The result is `split.zip`. In `single` mode, omitted pages selects every page. In `ranges` mode, comma-separated groups such as `1-2,3-5` produce one PDF per group.


### v0.3.0 page editor

Upload a PDF in the Page editor, load thumbnails, select pages, rotate or delete them, drag or use the move buttons to reorder, Undo edits, and save a new PDF.

New endpoints: `POST /api/pdf/info`, `POST /api/pdf/thumbnail`, `POST /api/pdf/organize`.

The browser sends the selected PDF to the configured FastAPI server. When deployed publicly, the file travels to that server; it is not processed entirely inside the browser.

### v0.4.0

Added lossless PDF optimization, printable ASCII text watermarks, and AES-256 password protection. Existing endpoints and page editor remain available. Compression may return the original bytes when optimization does not reduce size. Encrypted input PDFs are not supported.

### v0.5.0

- POST /api/pdf/text: extract selectable PDF text to UTF-8 TXT. Scanned pages require OCR.
- POST /api/pdf/unicode-watermark: embed text using an uploaded TTF/OTF font. Font must contain requested glyphs.
- POST /api/pdf/image-watermark: apply a PNG/JPEG watermark with size, opacity and position.
- Uploaded fonts and images are processed in memory; neither is stored by the application.

### v0.7.0 interface

The tools and page editor are separate workspace panels. PDF uploads support drag and drop, file details, responsive layouts, request status, and error feedback. Processing remains on the existing FastAPI endpoints. The progress animation indicates an active request, not measured server progress.

### v0.8.0

Improved operation-specific options, file-count guidance, disabled submit until files are selected, optional PDF metadata preview, and split range validation.


### v0.9.0

Merge files can be reordered or removed before processing. Download names use the input filename. A result can be downloaded again while the page remains open. Favicon, robots.txt and sitemap.xml are served at the site root. The public sitemap contains only the home page. robots.txt does not provide access control; protect the service separately if needed.


### v0.9.1 stability

- Regression tests for page reordering, deletion, and rotation with pre-rotated pages.
- Validate text, external URI annotations, page geometry, and document metadata after editing.
- Preserve document metadata when organizing or rotating pages.
- Keep compression compatible with the supported pypdf range.
- Run `python -m pytest -q` before deployment.

### v0.11.0 editor improvements

- Page move controls complement drag-and-drop reordering.
- Undo the last 30 rotate, delete, or reorder edits.
- Editor buttons reflect selection and loading state.
- Prevent deleting every page, and confirm before reloading unsaved edits.
- Show loading progress and clearer request errors.
- Preserve existing PDF operations and API contracts.
- Expanded automated tests for editor export and invalid files.

### Content editor (v0.11.0)

The initial v0.11.0 release introduced positioned ASCII text additions. Later releases expanded this to Unicode font uploads, image placement, text boxes, and region replacement. The current supported workflow is described below.

Content editor preview uses a 144 DPI PDF rendering and offers fit-width and 75–200% zoom. Text positions use normalized page coordinates and are independent of preview zoom.

#### Advanced Content editor (v0.12.0)

The Content editor supports Unicode text with a bundled or uploaded TTF/OTF font, movable and editable text additions, PNG/JPEG image insertion and resizing, rectangular replacement of original content, and Undo/Redo. Select / move mode allows dragging added items; drag the bottom-right corner of an image to resize it. Replace region mode permanently removes content within a selected rectangle in the exported copy, then optionally inserts new text. Review the result carefully before sharing. This is region-based redaction, not full reconstruction of the original PDF text layout, fonts, or structure. Noto Sans KR is selected automatically for Unicode text. The font menu also offers Noto Serif KR, Nanum Gothic, and a TTF/OTF upload mode.

#### Text box resizing

In Content editor, select a text addition using Select / move. Drag any of the eight handles to adjust its box dimensions. Font size remains controlled separately. Text boxes are exported with PDF text wrapping, and saving fails if the text cannot fit in the selected box. Browser preview wrapping is approximate and may differ from the exported PDF for some fonts.

#### Content editor integration (v0.13.1)

- Text boxes support horizontal left, center, and right alignment; vertical top, middle, and bottom alignment; and configurable line spacing (1.0–2.0).
- Built-in PDF fonts support bold and italic. For Unicode, upload an appropriately styled font file; synthetic bold and italic are intentionally rejected to avoid mismatches.
- Double-click an added text box in Select / move mode to edit its text in a dialog. This is not editing of original PDF text.
- Images can be rotated in 90-degree increments. Keep image proportions is enabled by default during corner resizing.
- Text box size and alignment changes remain undoable. The server rejects text that does not fit in the selected box.
- Original content replacement remains region-based redaction, not character-level editing. Redaction removes original material from the exported copy; review output before distribution.
- Canvas preview uses browser font metrics and is approximate. Validate final output in a PDF reader, particularly for Unicode font metrics, line breaks, and image rotations.
