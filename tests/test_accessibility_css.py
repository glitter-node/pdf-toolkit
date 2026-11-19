from html.parser import HTMLParser
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
root = Path(__file__).resolve().parents[1]


def luminance(value):
    value = value.lstrip("#")
    value = "".join(char * 2 for char in value) if len(value) == 3 else value
    channels = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]
    channels = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(foreground, background):
    first, second = luminance(foreground), luminance(background)
    return (max(first, second) + 0.05) / (min(first, second) + 0.05)


class StylesheetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stylesheets = []

    def handle_starttag(self, tag, attrs):
        if tag == "link":
            values = dict(attrs)
            if values.get("rel") == "stylesheet":
                self.stylesheets.append(values.get("href"))


def test_accessibility_colors_meet_wcag_text_and_ui_thresholds():
    assert contrast("#4b6590", "#e4eaf5") >= 4.5
    assert contrast("#5f6d84", "#f3f5f9") >= 4.5
    assert contrast("#5f6d84", "#ffffff") >= 4.5
    assert contrast("#4267ad", "#ffffff") >= 3
    assert contrast("#637aa5", "#f8faff") >= 3
    assert contrast("#637aa5", "#ffffff") >= 3


def test_accessibility_stylesheet_is_external_and_served():
    html = client.get("/")
    parser = StylesheetParser()
    parser.feed(html.text)
    assert "/static/css/accessibility.css" in parser.stylesheets
    css = client.get("/static/css/accessibility.css")
    assert css.status_code == 200
    assert "style=" not in html.text
    assert "<style" not in html.text
    assert "<script>" not in html.text
    assert "color: #5f6d84" in css.text
    assert "color: #4b6590" in css.text
