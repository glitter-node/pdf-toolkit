# v0.18.0 theme contrast audit

The WCAG 2.2 AA target is 4.5:1 for ordinary text and 3:1 for meaningful control boundaries. Ratios below use the CSS token colors and WCAG relative luminance. They are static token measurements, not browser computed styles.

| Theme | Text/surface | Muted/surface | Button text/primary | Border/surface | Focus/surface | Input text/input |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Light | 15.46 | 5.24 | 6.68 | 3.19 | 6.68 | 15.46 |
| Dark | 13.36 | 9.03 | 7.81 | 3.66 | 8.75 | 11.42 |
| Warm | 14.25 | 6.94 | 5.84 | 3.44 | 5.75 | 13.92 |

Dark colors: page `#101827`, surface `#1c2940`, input `#243451`, muted text `#c2cce0`, preview surround `#26334a`. Light colors: page `#f4f6fb`, surface/input `#ffffff`, preview surround `#d7dce5`. Warm colors: page `#f6f2ea`, surface `#fffdf8`, input `#fffaf0`, preview surround `#e8dfd2`.

Status colors (success, warning, error, progress), hover button text, disabled button text, and input borders are checked against their declared surfaces in `tests/test_theme_contrast.py`. Disabled controls are also identified by native disabled state; their distinct colors do not depend on opacity. Browser owned file chooser UI may vary by platform.

Browser verification remains required for computed colors, alpha compositing, all responsive widths, focus clipping, and four languages in three themes. On this host Chromium fails to start because `libatk-1.0.so.0` is missing. Run the existing browser tests on a supported machine and check the actual computed colors and contrast of the input, help, status, preview, page card, tab, and dialog elements.
