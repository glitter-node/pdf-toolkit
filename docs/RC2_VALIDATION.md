# v0.17.0 RC2 validation

The RC2 candidate was prepared separately from the production v0.16.0 source. No production configuration or process was changed.

## Browser execution

The NAS host has no Docker, Podman, or compatible Chromium runtime. A local isolated Uvicorn server starts successfully, but Chromium exits before any page loads because `libatk-1.0.so.0` is absent. The launch error is retained in `artifacts/e2e/browser-launch-error.txt`. No screenshot can be captured before browser startup.

On a separate machine with Docker, run from the RC2 source directory:

```bash
docker build -f Dockerfile.e2e -t pdf-toolkit-rc2-e2e .
mkdir -p artifacts/e2e
docker run --rm --init --ipc=host --network none --memory=2g --cpus=2 --pids-limit=256 --mount type=bind,src="$(pwd)/artifacts/e2e",dst=/artifacts -e PDF_TOOLKIT_E2E_ARTIFACTS=/artifacts pdf-toolkit-rc2-e2e
```

The image pins the official Playwright Python version to the test package version. The test starts its own Uvicorn server on a random loopback port, never port 8013. Container networking is disabled at runtime, so the tests cannot reach the production service. On failure, screenshots and browser/server logs are written to `artifacts/e2e`. The workflow manipulates the real Chromium UI for tabs, upload, preview, Unicode text, editing, movement, resizing, image placement and rotation, Undo/Redo, unsaved warning, save validation, failed save and retry, download, and Top navigation. Five separate browser tests check 1920×1080, 1366×768, 768×1024, 390×844, and 320×640.

## Public service risk

The active Nginx host `pdf-toolkit.glitter.kr` proxies all paths to `127.0.0.1:8013` with 60-second proxy timeouts. The examined host block has no authentication, allowlist, request rate limit, or connection limit. The global Nginx configuration sets `client_max_body_size 0` and disables proxy request buffering. Unauthenticated read-only requests returned 200 for `/`, `/docs`, `/openapi.json`, and the Content editor script; the API path returned 405 to GET, consistent with its POST route. The existing Uvicorn process runs with `--reload` and has no confirmed CPU, memory, or request-duration isolation. The app validates PDF signatures, size and page count, rejects encrypted and corrupted PDFs, limits rendered pixels, and rejects invalid edit coordinates. RC2 adds an in-process concurrency gate with default 2, configurable through `MAX_CONCURRENT_PDF_REQUESTS` from 1 to 16, plus early image count and byte limits. The HTTP 429 response does not alter successful API payloads.

The app-level gate applies per process and cannot enforce an OS CPU, memory, or hard execution-time limit for a blocking PDF parser. Nginx's proxy timeout does not stop the parser after a disconnected client. Public exposure without an approved authentication policy and isolated worker resources remains High risk. Do not deploy until the owner confirms whether access is private or public and the corresponding operational controls are implemented and verified. No Nginx policy was chosen or changed in RC2.

## Validation commands

```bash
python -m pytest -q
node --test tests/*.test.cjs
python -m compileall -q app tests
python -m pip check
node --check app/static/js/app.js
node --check app/static/js/back-to-top.js
node --check app/static/js/content-editor.js
node --check app/static/js/editor.js
python -m pytest -q tests/e2e_rc2.py
```

The browser command failed in setup on this host before any scenario ran. Its error is recorded without treating the E2E gate as passed. The Korean font fixture remains bundled under its Open Font License, and the Unicode embedding test has no skip. Existing PDF integrity, redaction, rotation, CropBox, and page preservation tests remain active. The production backup from RC1 is available at `/volume1/glitter/pdf-toolkit-v0160-backup-20261119T034102Z`; its 47-file SHA-256 manifest was verified. No rollback was needed because no deployment occurred.

The final RC2 standard suite passed 130 Python tests with zero failures and zero skips, plus 31 JavaScript tests with zero failures. Python reported five upstream PyMuPDF warnings. Python compileall, all four JavaScript syntax checks, and pip check passed. The separate E2E run stopped at browser setup with one error and zero scenarios executed; all five viewport cases were therefore unexecuted.
