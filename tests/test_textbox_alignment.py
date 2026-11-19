import fitz
from app.services.pdf import content_edit


def test_textbox_centered_horizontally_and_vertically():
    document = fitz.open()
    document.new_page(width=400, height=400)
    source = document.tobytes()
    document.close()
    result = content_edit(source, [{"type": "text", "page": 1, "x": 0.2, "y": 0.75, "w": 0.6, "h": 0.5, "text": "Centered", "size": 20, "color": "#000000"}])
    with fitz.open(stream=result, filetype="pdf") as output:
        words = output[0].get_text("words")
        assert len(words) == 1
        x0, y0, x1, y1 = words[0][:4]
        assert abs((x0 + x1) / 2 - 200) < 3
        assert abs((y0 + y1) / 2 - 200) < 12
