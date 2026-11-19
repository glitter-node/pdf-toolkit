# PDF Toolkit UI design system

PDF Toolkit v1.0.0 keeps the existing editor and API contracts while providing shared tokens in `app/static/css/theme.css`. The current application and UI version share `APP_VERSION` in `app/core/version.py`; the HTML badge is rendered by Jinja2.

Themes are selected with `data-theme` on the document root. Supported values are `light`, `dark`, and `warm`; invalid stored values fall back to `light`. PDF canvases and image output are never filtered by a theme.

Translations are JSON resources in `app/static/locales/` with the same semantic key set for `ko`, `en`, `ja`, and `zh-CN`. Korean is the explicit default and fallback. Static and dynamic UI use the shared `pdfToolkitI18n` API. New languages must copy the complete key set and be added to the allow-list in `app/static/js/preferences.js`.

User-facing operation labels and runtime status updates are translated by the same preferences layer without changing API operation identifiers. Dynamic values such as file names and server error details remain text nodes and are not interpreted as HTML.

The layout uses flexible grid and flex containers. The mobile breakpoint is 767px, with tablet and desktop layouts above it. Interactive controls target a 44px minimum touch height, while PDF preview scrolling remains inside its own container.

The `body` supplies the shared viewport gutter (24px, or 12px at 767px and below). `main` owns the 1440px maximum width, uses zero padding and a bottom margin of 18px. Its direct children, the header, navigation, and workspace panels, share the same left edge; the header and panels retain their own internal padding. The header has 10px vertical padding and an 18px bottom margin; navigation has its own 18px bottom margin. Layout geometry lives in `theme.css`, while `app.css` retains component structures. Theme variants change colors and shadows only. Avoid duplicate geometry declarations across the two files and avoid hiding overflow to mask layout defects.

For browser verification, compare `getComputedStyle(main).paddingLeft`, `getComputedStyle(main).marginBottom`, and the header padding and margin with their expected 0px, 18px, 10px, and 18px values. Compare the left edges of `.site-header`, `.workspace-nav`, and the visible `.workspace-panel` with `getBoundingClientRect()` at 1440, 1280, 1024, 768, 390, and 360px. Check `document.documentElement.scrollWidth <= innerWidth` and keep PDF preview scrolling inside its own container.

Focus-visible outlines, live status regions, reduced-motion preferences, and color tokens are maintained for WCAG 2.2 AA-oriented checks. Scripts and styles are external and use only same-origin resources under the enforced CSP.

Contrast tokens cover text, supporting text, inputs, disabled controls, status colors, meaningful borders, and focus rings. `--color-preview` colors only the area around the PDF; PDF canvas and images retain their original colors. Buttons use `--color-primary` with `--color-on-primary`, `--color-primary-hover` on hover, and distinct disabled colors without reducing the entire control opacity. The contrast audit and its limits are in `ACCESSIBILITY_AUDIT.md`.
