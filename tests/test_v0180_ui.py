import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_locale_sets_are_complete_and_identical():
    locales = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((ROOT / "app/static/locales").glob("*.json"))]
    assert len(locales) == 4
    keys = set(locales[0])
    assert all(set(locale) == keys for locale in locales)


def test_locale_values_and_placeholders_are_complete_without_duplicate_keys():
    catalogs = []
    for path in sorted((ROOT / "app/static/locales").glob("*.json")):
        pairs = []
        catalog = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=lambda values: pairs.extend(values) or dict(values))
        assert len(pairs) == len({key for key, _ in pairs})
        assert all(isinstance(value, str) and value.strip() for value in catalog.values())
        catalogs.append(catalog)
    for key in catalogs[0]:
        expected = set(re.findall(r"\{([a-zA-Z][a-zA-Z0-9_]*)\}", catalogs[0][key]))
        assert all(set(re.findall(r"\{([a-zA-Z][a-zA-Z0-9_]*)\}", catalog[key])) == expected for catalog in catalogs)


def test_template_and_assets_keep_csp_safe_external_resources():
    html = (ROOT / "app/templates/index.html").read_text(encoding="utf-8")
    assert '<html lang="ko">' in html
    assert '/static/css/theme.css' in html
    assert '/static/js/preferences.js' in html
    assert "<script>" not in html
    assert 'style="' not in html
    assert "https://cdn" not in html


def test_theme_tokens_and_responsive_rules_exist():
    css = (ROOT / "app/static/css/theme.css").read_text(encoding="utf-8")
    for token in ("--color-background", "--color-surface", "--color-primary", "--color-focus", "--shadow-card"):
        assert token in css
    assert 'data-theme="dark"' in css
    assert 'data-theme="warm"' in css
    assert "max-width: 767px" in css
    assert "prefers-reduced-motion" in css


def test_runtime_translation_layer_covers_upload_and_operation_labels():
    js = (ROOT / "app/static/js/preferences.js").read_text(encoding="utf-8")
    locale = json.loads((ROOT / "app/static/locales/ko.json").read_text(encoding="utf-8"))
    for key in ("upload.none", "upload.drop", "upload.many", "tools.merge", "tools.imageWatermark"):
        assert key in locale
        assert key in js


def test_header_controls_have_constrained_desktop_selectors():
    css = (ROOT / "app/static/css/theme.css").read_text(encoding="utf-8")
    assert ".header-controls {" in css
    assert "flex-wrap: nowrap" in css
    assert ".header-controls select { box-sizing: border-box; appearance: auto; width: auto;" in css
    assert "max-width: 11rem" in css


def test_back_to_top_uses_transparent_theme_aware_states():
    css = (ROOT / "app/static/css/theme.css").read_text(encoding="utf-8")
    assert ".back-to-top { background: transparent; color: var(--color-primary);" in css
    assert ".back-to-top:hover:not(:disabled) { background: var(--color-primary); color: var(--color-on-primary);" in css
    assert ".back-to-top:active { background: var(--color-primary-hover); color: var(--color-on-primary);" in css
    assert "box-shadow: none" in css
    assert ".back-to-top:focus-visible" in css


def test_header_selects_keep_native_controls_and_connected_labels():
    html = (ROOT / "app/templates/index.html").read_text(encoding="utf-8")
    css = (ROOT / "app/static/css/theme.css").read_text(encoding="utf-8")
    assert 'id="language-label" for="language-select"' in html
    assert 'id="theme-label" for="theme-select"' in html
    assert 'aria-labelledby="language-label"' in html
    assert 'aria-labelledby="theme-label"' in html
    assert "appearance: auto" in css
    assert "height: 44px" in css
    assert "padding: 10px 36px 10px 14px" in css
    assert "header-control" in css


def test_main_layout_has_one_owner_and_preserves_section_spacing():
    app_css = (ROOT / "app/static/css/app.css").read_text(encoding="utf-8")
    theme_css = (ROOT / "app/static/css/theme.css").read_text(encoding="utf-8")
    assert "main{" not in app_css
    assert "main { width: 100%; max-width: var(--layout-max-width); margin: 0 0 18px; padding: 0; }" in theme_css
    assert "body { background: var(--color-background); color: var(--color-text); padding-inline: var(--layout-gutter); }" in theme_css


def test_site_header_spacing_is_compact_without_changing_mobile_side_padding():
    css = (ROOT / "app/static/css/theme.css").read_text(encoding="utf-8")
    assert "padding: 10px 22px; margin: 0 0 18px;" in css
    assert "padding: 10px 16px;" in css
    assert "padding: 18px 22px" not in css
    assert "margin-bottom: 16px" not in css


def test_main_is_the_shared_horizontal_alignment_container():
    css = (ROOT / "app/static/css/theme.css").read_text(encoding="utf-8")
    assert "--layout-gutter: 24px" in css
    assert "--layout-gutter: 12px" in css
    assert "main { width: 100%; max-width: var(--layout-max-width); margin: 0 0 18px; padding: 0; }" in css
    assert ".site-header" in css and ".workspace-nav" in css and ".workspace-panel" in css
