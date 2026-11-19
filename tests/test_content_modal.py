from pathlib import Path


def test_content_text_modal_markup():
    html = Path('app/templates/index.html').read_text()
    assert 'id="content-text-dialog"' in html
    assert 'id="content-dialog-value"' in html
    assert 'id="content-dialog-cancel"' in html
    assert 'id="content-dialog-form"' in html


def test_content_text_modal_script():
    script = Path('app/static/js/content-editor.js').read_text()
    assert 'contentAskText(edit.text, "Edit selected text")' in script
    assert 'contentAskText(contentText.value, "Add text")' in script
    assert 'contentTextDialog.showModal()' in script
    assert 'contentCloseTextDialog(null)' in script
