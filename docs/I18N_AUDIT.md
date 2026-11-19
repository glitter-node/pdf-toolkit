# v0.18.0 i18n audit

The audit covered the header, navigation, PDF tools, upload state, operation options, Page editor cards and status, Content editor controls and modal, download state, validation messages, titles, placeholders, and accessibility names.

Operation values and API request fields remain unchanged. Page card labels, movement names, page progress, edit counts, page position, modal actions, confirmation messages, and common client-side validation now use translation keys. Language changes update existing rendered controls without reloading the page.

Browser-owned file picker text is outside the application catalog. Server-provided unstructured error detail is preserved rather than translated by matching internal exception text. Client-owned connection and validation messages are localized.

Automated checks reject invalid JSON, duplicate keys, empty values, mismatched key sets, and placeholder mismatches. Actual Chromium verification remains blocked on this host when `libatk-1.0.so.0` is unavailable.
