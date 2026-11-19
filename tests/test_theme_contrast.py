import re
from pathlib import Path


CSS = (Path(__file__).resolve().parents[1] / "app/static/css/theme.css").read_text(encoding="utf-8")


def tokens(theme):
    base = re.search(r":root\s*\{([^}]+)\}", CSS).group(1)
    values = dict(re.findall(r"(--color-[\w-]+):\s*(#[0-9a-fA-F]{6})", base))
    if theme != "light":
        override = re.search(rf':root\[data-theme="{theme}"\]\s*\{{([^}}]+)\}}', CSS).group(1)
        values.update(re.findall(r"(--color-[\w-]+):\s*(#[0-9a-fA-F]{6})", override))
    return values


def luminance(color):
    channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
    return sum(channel * weight for channel, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast(a, b):
    low, high = sorted((luminance(a), luminance(b)))
    return (high + 0.05) / (low + 0.05)


def test_theme_text_controls_and_boundaries_meet_required_contrast():
    for theme in ("light", "dark", "warm"):
        palette = tokens(theme)
        for foreground, background in (("text", "surface"), ("muted", "surface"), ("text", "input"), ("on-primary", "primary"), ("on-primary", "primary-hover"), ("disabled-text", "disabled")):
            assert contrast(palette[f"--color-{foreground}"], palette[f"--color-{background}"]) >= 4.5, (theme, foreground, background)
        assert contrast(palette["--color-border"], palette["--color-surface"]) >= 3
        assert contrast(palette["--color-border"], palette["--color-input"]) >= 3
        assert contrast(palette["--color-focus"], palette["--color-surface"]) >= 3
        for state in ("success", "warning", "danger", "info"):
            assert contrast(palette[f"--color-{state}"], palette["--color-surface"]) >= 4.5, (theme, state)


def test_preview_and_canvas_are_not_filtered():
    assert "filter:" not in re.search(r"\.content-preview\s*\{([^}]+)\}", CSS).group(1)
    assert "canvas { filter" not in CSS
