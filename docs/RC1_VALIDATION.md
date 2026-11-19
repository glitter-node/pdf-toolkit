# v0.17.0 RC1 validation record

This record describes the isolated RC1 candidate. The live service stayed on v0.16.0.

## Test environment

- Python 3.11.10, Node.js 22.23.4, PyMuPDF 1.26.0, pypdf 6.21.4, FastAPI 0.164.0, Starlette 1.10.0.
- Existing production Uvicorn binds to `127.0.0.1:8013` with `--reload`; the isolated benchmark server used `127.0.0.1:18013`.
- The existing public Nginx proxy forwards requests to the production service without authentication or resource isolation. This is a High resource exhaustion risk and blocks deployment under the release gate.
- No Git repository was found.

## Automated checks

Run from the project root with the test dependencies in `requirements-test.txt` installed:

```bash
python -m pytest -q
node --test tests/*.test.cjs
python -m compileall -q app tests
python -m pip check
node --check app/static/js/app.js
node --check app/static/js/back-to-top.js
node --check app/static/js/content-editor.js
node --check app/static/js/editor.js
```

The Korean embedding test uses `tests/fixtures/NanumGothic-Regular.ttf` by default. To use a different local font, set `PDF_TOOLKIT_TEST_KOREAN_FONT` to its path. The fixture is sourced from the official Google Fonts Nanum Gothic repository and distributed with its Open Font License in `tests/fixtures/NanumGothic-OFL.txt`.

On this host the RC1 candidate passed 127 Python tests and 31 JavaScript tests, with zero failures and zero skips. Python compileall, all four application JavaScript syntax checks, and pip check passed. The Python run reported five upstream SWIG warnings.

## Browser gate

Playwright 1.65.2 and Chromium were downloaded. The host cannot launch Chromium because `libatk-1.0.so.0` is absent. The host is a NAS environment with glibc 2.27, without a supported package manager or container runtime for Playwright's browser dependencies. The 20 required browser scenarios and five viewport checks were not run. JavaScript DOM tests do not substitute for browser E2E. Acrobat was not run.

## Dependency warnings

The pre-change suite emitted six warnings: five PyMuPDF SWIG builtin-type `DeprecationWarning` messages from `<frozen importlib._bootstrap>:241` (`SwigPyPacked` twice, `SwigPyObject` twice, `swigvarlink` once), plus one `StarletteDeprecationWarning` from `venv/lib/python3.11/site-packages/fastapi/testclient.py:1` about the legacy httpx TestClient. Installing the test-only `httpx2==2.16.2` integration resolved the Starlette warning without application API changes. Five upstream PyMuPDF warnings remain; none indicates an observed application failure or a verified vulnerability. No warning filters were added.

## Performance snapshot

The benchmark script is guarded against the production port. Run `PDF_TOOLKIT_BENCHMARK_PID=<isolated-server-pid> python tests/benchmark_rc1.py` against the isolated server. Times are single local measurements, not throughput guarantees.

| PDF sample | Info ms | Preview ms | Save ms | Result bytes | RSS MB |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 page | 7.4 | 32.6 | 11.9 | 965 | 103.4 |
| 10 pages | 6.0 | 25.9 | 12.9 | 3754 | 104.4 |
| 50 pages | 16.2 | 70.6 | 29.9 | 16195 | 104.7 |
| 100 pages | 53.0 | 69.6 | 92.7 | 31941 | 105.7 |
| Image | 5.9 | 42.9 | 18.7 | 3865 | 106.0 |
| Unicode | 5.7 | 39.1 | 256.0 | 718589 | 105.4 |
| Rotated | 4.0 | 27.9 | 10.4 | 977 | 107.6 |

Ten repeated saves left the measured process RSS at 107.6 MB. Output page counts were reopened with both PyMuPDF and pypdf. The Unicode case was slowest because the font was embedded.

## Deployment gate

The browser E2E gate and the no-High-vulnerability gate did not pass. The ZIP is for review and testing in a supported isolated environment. Do not deploy it to the existing public service until authentication, resource isolation, browser E2E, and a reviewed service restart path are in place. No production source, configuration, user files, service process, or Nginx setting was changed. A verified source and settings backup was prepared separately for rollback readiness; no rollback was needed.
