# Third-party licenses

PDF Toolkit's own source code is licensed under the MIT License in [LICENSE](LICENSE). That license does not change the license of a dependency or bundled asset.

## Dependencies

The dependency versions are declared in [requirements.txt](requirements.txt). Their copyright and license terms remain those supplied by each project and distribution.

PyMuPDF 1.26.0 is installed for the current environment. Its local `COPYING` file identifies it as dual licensed under the GNU Affero GPL 3.0 or the Artifex Commercial License. Users who distribute or operate a build using PyMuPDF must select and comply with the applicable PyMuPDF terms. This project does not grant an AGPL or commercial PyMuPDF license and does not replace PyMuPDF's notice.

FastAPI, Uvicorn, pypdf, ReportLab, Pillow, Jinja2 and cryptography are third-party dependencies. Their individual license notices are supplied by their respective distributions; this file does not relicense them as MIT. Review the installed distribution notices and the applicable upstream terms before redistributing a packaged build.

## Bundled fonts

- Noto Sans KR: SIL Open Font License 1.1; see [app/assets/fonts/NotoSansKR-OFL.txt](app/assets/fonts/NotoSansKR-OFL.txt).
- Noto Serif KR: SIL Open Font License 1.1; see [app/assets/fonts/NotoSerifKR-OFL.txt](app/assets/fonts/NotoSerifKR-OFL.txt).
- Nanum Gothic: SIL Open Font License 1.1; see [tests/fixtures/NanumGothic-OFL.txt](tests/fixtures/NanumGothic-OFL.txt).

The font files are not covered by the project's MIT License. Keep each font's license notice when copying or redistributing the corresponding font. The licenses for documents created with the fonts are separate from the font licenses.

## Scope

No external font, image, icon, CDN asset, or system-wide installation is required by the project source. Before adding another asset, record its license and retain any required notice in the project.
