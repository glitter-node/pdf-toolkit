## Unreleased local source changes

- Bundle licensed Noto Sans KR and Noto Serif KR fonts, reuse the licensed Nanum Gothic fixture, and add allowlisted Unicode font selection for Content editor and Unicode watermark.
- Preserve uploaded font API compatibility and reject conflicting choices, unsupported glyphs, and unsupported Unicode styles.
- Add the MIT License and clarify project, dependency, and bundled-font licensing in the documentation.

## v1.0.0 (release preparation)

- Centralized the current application version in `app/core/version.py` and synchronized FastAPI, OpenAPI, the UI badge, tests, and current documentation.
- Kept existing PDF processing, editor behavior, security policy, and historical release records unchanged.

## v0.17.0 RC2

- Add a configurable per-process limit for simultaneous PDF API requests, returning HTTP 429 when it is reached.
- Reject more than 20 uploaded edit images before reading them, and reject oversized individual or aggregate image uploads as each image is read.
- Add an isolated Playwright Chromium workflow and five viewport checks, plus a pinned official Playwright container recipe for a supported test machine.
- Keep production v0.16.0 unchanged because the browser and public access deployment gates remain open.

## v0.17.0 RC1

- Check render dimensions before pixmap allocation to reject oversized pages without first consuming the rendering memory.
- Add security regression coverage for malformed PDFs and edits, size and page limits, encrypted PDFs, uploaded assets, and fixed download filenames.
- Bundle a Korean test font under its Open Font License and run the Unicode PDF embedding test without a font-related skip.
- Record browser, dependency warning, performance, security, and deployment-gate results in `docs/RC1_VALIDATION.md`. Production deployment remains blocked pending browser E2E and public resource isolation.

## v0.16.0

- Improved the centered text dialog with adaptive textarea rows, focus handling, and backdrop cancellation.
- Protected unsaved Content editor changes on file replacement, reload, and page exit while retaining edits across page and tab changes.
- Added client save validation, clearer save state, duplicate request protection, and stale response handling.
- Improved small-screen controls, touch pointer handling, keyboard focus, and status announcements.
- Expanded DOM regression tests for modal, keyboard, file replacement, save failure, and request races.

## v0.15.0

- Measured PDF text with the actual selected font for long-string wrapping and rejected missing uploaded-font glyphs.
- Added internal edit IDs without changing the save API payload, fixed proportional image enlargement, and restored in-progress edits on page and mode changes or save.
- Added rotation, CropBox, Unicode embedding, redaction, and PDF integrity regression tests.
- Allowed a locally licensed Korean test font through `PDF_TOOLKIT_TEST_KOREAN_FONT` without bundling a font.

## v0.14.0

- Accepted multiline text in the Content editor and PDF export, with browser font measurement, page-aware sizing, and preserved manually adjusted width.
- Added keyboard movement, deletion, Undo/Redo, and Escape handling outside text inputs and dialogs.
- Restored edits after cancelled pointer actions and guarded modal and image loading against file or page changes.
- Kept inserted images after region redaction, mapped edits on rotated pages to visual preview coordinates, and added PDF integrity and editor interaction regression tests.
- Improved text dialog scrolling on small screens.

## v0.13.3

- Added a transparent fixed Back to top button at the bottom-right of the browser viewport.
- Button appears after scrolling and supports smooth scrolling, keyboard access, and reduced motion.
- No changes to PDF editing or export APIs.

## v0.13.2

- Replace the browser text prompt with a centered, responsive text editing dialog.
- Open the same dialog when adding text on the page, with multiline Unicode input and cancel support.
- Keep automatic text box sizing, text formatting, and undo/redo behavior.

## v0.13.1 — Automatic Text Box Sizing

- Automatically size text boxes when adding or updating text.
- Expand width for longer content and increase height when wrapping is needed near the page edge.
- Preserve manual resizing, alignment, and Undo/Redo.
- Retain all existing PDF operations and editor APIs.

## v0.13.0 — Integrated Content Editor

- Added horizontal and vertical text alignment controls and line spacing.
- Added bold and italic support for built-in PDF fonts with validation for uploaded Unicode fonts.
- Added double-click text editing dialog and 90-degree image rotation.
- Added proportional image resize toggle and formatting regression tests.
- Preserved the existing PDF tools, Page editor, content redaction workflow, and Undo/Redo.

## v0.11.0

- Improved Content editor with a higher-resolution preview, fit-width display, and selectable zoom levels.
- Preserved normalized text placement coordinates across preview zoom levels.
- Added preview resolution and PDF coordinate regression coverage.

- Added a separate Content editor with page previews, positioned text additions, color and size settings, undo, and PDF export.
- Added API validation and content editing tests.
- Preserved existing PDF tools and Page editor.

# Changelog

## v0.10.0

- Stabilized Page editor loading so stale PDF information and thumbnails cannot replace the latest file's state.
- Added page move controls and Undo for the last 30 rotation, deletion, or reorder edits.
- Improved loading and error handling, with automated editor race regression tests.
- Updated the README to match the supported PDF tools and local hosting limits.

## v0.12.0 — Advanced Content Editor

- Added Unicode text insertion with a user-supplied TTF/OTF font.
- Added selection, drag movement, text updates, and deletion of added edits.
- Added PNG/JPEG image insertion, movement, and corner resizing.
- Added rectangular redaction and optional replacement text for original content.
- Added bounded Undo/Redo history for content edits.
- Preserved the existing PDF tools and Page editor APIs.
- Redaction is destructive in the exported copy. Keep an untouched original and inspect the output before distribution.

### Text box resize stabilization
- Added eight resize handles to selected text boxes.
- Added width and height editing with drag and Undo/Redo support.
- Added PDF text box export and overflow validation.

### v0.12.0 — Text box alignment refinement
- Centered added text horizontally and vertically inside resized text boxes in the editor preview and exported PDF.
- Preserved resize handles, drag movement, and existing editing APIs.
- Added a PDF output alignment regression test.
## v0.17.0 RC3

- Replace FastAPI's CDN-backed Swagger UI and ReDoc pages at `/docs` and `/redoc` with local, read-only OpenAPI schema pages built with safe DOM APIs.
- Add an enforced same-origin CSP with no unsafe-inline or unsafe-eval, plus consistent MIME, referrer, frame, permissions, COOP/CORP, and content-specific cache headers.
- Add CSP, local-resource, response-header, download, error, and documentation DOM regression tests.
- Add `upgrade-insecure-requests` only when DSM forwards HTTPS, preserving direct loopback HTTP. The RC3 source was applied to the existing operating path by explicit instruction while browser and public access/resource isolation gates remain unresolved.

## v0.18.0

- Added a token-based Light, Dark, and Warm theme system with persisted preferences.
- Added Korean-default internationalization with English, Japanese, and Simplified Chinese locale resources.
- Added responsive workspace controls and reduced-motion support while preserving PDF editor behavior and enforced CSP.
- Completed key-based localization for PDF operation options, Page editor dynamic cards and status, Content editor controls, validation, modal, and accessibility labels.
- Unified theme colors for inputs, supporting text, states, borders, and preview surroundings, with automated WCAG contrast checks for all three themes.

