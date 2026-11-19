# i18n test matrix

Run `venv/bin/python -m pytest -q` and `node --test tests/*.test.cjs` before release.

For each of Korean, English, Japanese, and Simplified Chinese, verify the three tabs, all PDF operation options, upload instructions, Page editor cards, Content editor alignment and formatting options, modal actions, status updates, validation errors, download state, and accessibility names.

On Windows Chrome, open DevTools, select each language, reload, and confirm the language persists. Upload a PDF, switch tabs and languages, then confirm the selected operation, file, page, edit mode, text, and Undo/Redo state remain intact. Repeat in Light, Dark, and Warm themes and check the Console for CSP violations.

Verify responsive layouts at 375, 390, 768, 1024, 1440, and 1920 pixels. Browser-provided file picker text may follow the operating system rather than the application locale.
