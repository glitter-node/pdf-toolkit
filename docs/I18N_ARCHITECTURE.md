# Internationalization architecture

PDF Toolkit loads same-origin JSON catalogs from `app/static/locales/`. Korean is the fallback and explicit default. `preferences.js` exposes one `pdfToolkitI18n` API with `t`, `translate`, `getLanguage`, and `setLanguage` methods.

Translation keys use feature namespaces such as `tools.*`, `pdfTools.*`, `pageEditor.*`, `content.*`, `options.*`, `validation.*`, and `accessibility.*`. All four catalogs must contain identical non-empty key sets and identical placeholder names.

Use `pdfToolkitI18n.t("namespace.key", {count: value}, "English fallback")` for dynamic output. Values are assigned through `textContent`, DOM text nodes, or attributes. Translation strings must not contain HTML. API paths, internal identifiers, file names, MIME types, and PDF content are never translated.

Language changes dispatch `pdf-toolkit-language-change`. Renderers update labels and status text without replacing files, pages, edit data, or Undo/Redo history. Invalid stored locale values recover to Korean. If a selected catalog fails to load, Korean remains usable.

To add a string, add the same key and placeholders to all four JSON files, bind static DOM in `applyStatic`, or call `t` from a dynamic renderer, then run the Python and JavaScript tests.
