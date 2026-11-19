(function () {
  'use strict';
  const themes = ['light', 'dark', 'warm'];
  const languages = ['ko', 'en', 'ja', 'zh-CN'];
  const storage = window.localStorage;
  const root = document.documentElement;
  const safeGet = (key, fallback, allowed) => { try { const value = storage.getItem(key); return allowed.includes(value) ? value : fallback; } catch (error) { return fallback; } };
  const safeSet = (key, value) => { try { storage.setItem(key, value); } catch (error) {} };
  let language = safeGet('pdf-toolkit-language', 'ko', languages);
  let messages = {};
  let korean = {};
  const theme = safeGet('pdf-toolkit-theme', 'light', themes);
  root.dataset.theme = theme;
  root.lang = language;
  const format = (value, params) => Object.entries(params || {}).reduce((text, [name, replacement]) => text.replaceAll(`{${name}}`, typeof replacement === 'number' ? new Intl.NumberFormat(language).format(replacement) : String(replacement)), value);
  const t = (key, params = {}, fallback = '') => format(messages[key] || korean[key] || fallback || key, params);
  const literalKeys = {
    'Selected Unicode font does not support Bold or Italic':'fonts.styleUnsupported','No files selected':'upload.none','Select at least two PDF files to merge.':'upload.many','Select one PDF file.':'upload.one','Only PDF files are supported.':'files.onlyPdf','This operation accepts one PDF. The first file was selected.':'files.singleLimited','Select the required PDF files.':'files.required','Processing... Please wait.':'status.processing','Completed. Your download should begin automatically.':'status.completed','Processing failed':'status.failed','Enter the required page ranges.':'validation.pageRanges','Enter 1-120 printable ASCII characters.':'validation.ascii','Select a font and enter watermark text.':'validation.fontAndText','Select a PNG or JPEG image.':'validation.image','Password must contain 8-128 characters.':'validation.password','Page order changed. Save to export.':'pageEditor.orderChanged','Selected pages rotated. Save to export.':'pageEditor.rotated','Last edit undone.':'pageEditor.undone','Loading pages...':'pageEditor.loading','Saving...':'pageEditor.saving','PDF saved successfully.':'pageEditor.saved','Select a PDF first.':'pageEditor.selectPdf','No pages to save.':'pageEditor.noPages','At least one page must remain.':'pageEditor.keepOne','Discard unsaved page edits?':'pageEditor.discard','Loading PDF...':'content.loading','Loading preview...':'content.loadingPreview','Select an editing mode to continue.':'content.ready','Edit added. Save to export.':'content.added','Selected text updated.':'content.updated','Saving content...':'content.saving','Content PDF saved successfully.':'content.saved','PDF saved. Newer edits are still unsaved.':'content.unsavedAfterSave','Discard unsaved content edits?':'content.discard','Permanently remove original PDF content inside this region in the exported copy?':'content.redactConfirm','Enter text to add.':'content.enterText','Maximum 200 edits.':'content.maxEdits','Choose a TTF or OTF font under 10 MB.':'content.fontError','Choose a PNG or JPEG image under 10 MB.':'content.imageError','No document loaded':'content.noDocument','Connection failed. Check the server and try again.':'content.connectionFailed','PDF contains no editable pages.':'content.noEditablePages','Unable to display page preview.':'content.unablePreview','Current edits were kept. Save or choose another PDF again.':'content.currentKept','Maximum 20 image uploads.':'content.maxImages','Choose a position inside the page.':'content.choosePosition','Unable to add content.':'content.unableAdd','Load a PDF before saving.':'content.loadBeforeSave','Add an edit before saving.':'content.addBeforeSave','Invalid edit page or type.':'content.invalidPageType','An edit is outside the page.':'content.outsidePage','An edit rectangle is outside the page.':'content.rectangleOutside','Choose a valid PNG or JPEG image before saving.':'content.invalidImage','An edit contains invalid text.':'content.invalidText','An edit has invalid text formatting.':'content.invalidFormatting','An edit has invalid text alignment or spacing.':'content.invalidAlignment','Upload a Unicode font before saving this text.':'content.unicodeBeforeSave','Use a styled font file for Bold or Italic text.':'content.styledFont','A text box is outside the page.':'content.textOutside','A text box is too short. Enlarge it or reduce the font size.':'content.textShort','Text may not fit in its box. Enlarge it or reduce the font size.':'content.textFit','Enter up to 250 characters with optional line breaks.':'content.textLength','Font size must be between 6 and 72.':'content.fontSizeRange','Upload a Unicode font to add non-ASCII text.':'content.unicodeFontRequired','Use a styled font file instead of Bold or Italic with an uploaded font.':'content.uploadedFontStyle','Line spacing must be between 1 and 2.':'content.lineSpacingRange','Add text':'modal.add','Edit selected text':'modal.editText','Update text':'modal.update'
  };
  const translate = value => literalKeys[value] ? t(literalKeys[value], {}, value) : value;
  const setText = (selector, key) => { const node = document.querySelector(selector); if (node) node.textContent = t(key, {}, node.textContent); };
  const setLabelText = (selector, key) => { const node = document.querySelector(selector); if (!node) return; const textNode = Array.from(node.childNodes).find(child => child.nodeType === Node.TEXT_NODE); if (textNode) textNode.nodeValue = ` ${t(key, {}, textNode.nodeValue.trim())}`; };
  const setOption = (selector, value, key) => { const option = document.querySelector(`${selector} option[value="${value}"]`); if (option) option.textContent = t(key, {}, option.textContent); };
  const setAttribute = (selector, name, key) => { const node = document.querySelector(selector); if (node) node.setAttribute(name, t(key, {}, node.getAttribute(name) || '')); };
  function applyStatic() {
    const textBindings = {'#language-label':'language.label','#theme-label':'theme.label','[data-panel="tools"]':'nav.pdfTools','[data-panel="editor"]':'nav.pageEditor','[data-panel="content-editor"]':'nav.contentEditor','#tools .section-heading h2':'tools.title','#tools .section-heading p':'tools.description','#drop-zone strong':'upload.drop','#drop-zone > span:not(.drop-icon)':'upload.browse','#file-summary':'upload.none','#merge-order h3':'pdfTools.mergeOrder','#merge-order p':'pdfTools.mergeHelp','#options-area > h3':'common.options','#process-button':'common.process','#download-link':'common.downloadAgain','#editor-title':'nav.pageEditor','#editor > p':'editor.pageDescription','#editor-load':'editor.loadPages','#editor-select-all':'editor.selectAll','#editor-rotate':'editor.rotate','#editor-delete':'editor.delete','#editor-undo':'editor.undoLast','#editor-save':'editor.save','#editor .editor-help':'editor.help','#content-title':'nav.contentEditor','#content-editor > p':'content.description','#content-load':'content.load','#content-prev':'content.previous','#content-next':'content.next','#content-mode-text':'content.addText','#content-mode-select':'content.selectMove','#content-mode-image':'content.addImage','#content-mode-replace':'content.replace','#content-apply':'content.update','#content-delete':'content.delete','#content-image-rotate':'content.rotate','#content-editor .editor-help':'content.longHelp','#content-undo':'common.undo','#content-redo':'common.redo','#content-save':'content.save','#content-dialog-title':'modal.editText','#content-dialog-hint':'modal.hint','#content-dialog-cancel':'common.cancel','#content-dialog-submit':'modal.update','#back-to-top span:last-child':'top'};
    const labelBindings = {'[for="operation"]':'tools.operation','[for="files"]':'upload.pdfFiles','[for="pages"]':'pdfTools.pages','[for="mode"]':'pdfTools.splitMode','[for="angle"]':'pdfTools.rotation','[for="image_format"]':'pdfTools.imageFormat','[for="page"]':'pdfTools.page','[for="unicode-text"]':'pdfTools.watermarkText','[for="unicode-font-id"]':'fonts.label','[for="unicode-font"]':'pdfTools.fontFile','[for="unicode-size"]':'pdfTools.fontSize','[for="unicode-opacity"]':'pdfTools.opacity','[for="unicode-position"]':'pdfTools.position','[for="watermark-image"]':'pdfTools.watermarkImage','[for="image-scale"]':'pdfTools.relativeWidth','[for="image-opacity"]':'pdfTools.opacity','[for="image-position"]':'pdfTools.position','[for="watermark-text"]':'pdfTools.watermarkText','[for="watermark-size"]':'pdfTools.fontSize','[for="watermark-opacity"]':'pdfTools.opacity','[for="watermark-position"]':'pdfTools.position','[for="protect-password"]':'pdfTools.password','[for="editor-file"]':'editor.pdfToEdit','[for="content-file"]':'content.pdfToEdit','[for="content-text"]':'content.text','[for="content-size"]':'content.fontSize','[for="content-color"]':'content.textColor','[for="content-align"]':'content.horizontal','[for="content-valign"]':'content.vertical','[for="content-leading"]':'content.lineSpacing','[for="content-font-id"]':'fonts.label','[for="content-font"]':'pdfTools.fontFile','[for="content-image"]':'content.image','[for="content-zoom"]':'content.zoom','[for="content-dialog-value"]':'modal.text'};
    Object.entries(textBindings).forEach(([selector, key]) => setText(selector, key));
    Object.entries(labelBindings).forEach(([selector, key]) => setText(selector, key));
    setLabelText('label:has(#content-bold)', 'options.bold');
    setLabelText('label:has(#content-italic)', 'options.italic');
    setLabelText('.content-lock', 'content.keepRatio');
    const operations = ['merge','extract','split','rotate','render','compress','watermark','protect','text','unicode-watermark','image-watermark'];
    const operationKeys = ['tools.merge','tools.extract','tools.split','tools.rotate','tools.render','tools.compress','tools.watermark','tools.protect','tools.text','tools.unicodeWatermark','tools.imageWatermark'];
    operations.forEach((value, index) => setOption('#operation', value, operationKeys[index]));
    for (const selector of ['#content-font-id', '#unicode-font-id']) {
      for (const [value, key] of [['default', 'fonts.default'], ['noto-serif-kr', 'fonts.serif'], ['nanum-gothic', 'fonts.nanum'], ['upload', 'fonts.upload']]) setOption(selector, value, key);
    }
    [['#theme-select','light','theme.light'],['#theme-select','dark','theme.dark'],['#theme-select','warm','theme.warm'],['#mode','single','pdfTools.onePerPage'],['#mode','ranges','pdfTools.onePerRange'],['#content-align','left','options.left'],['#content-align','center','options.center'],['#content-align','right','options.right'],['#content-valign','top','options.top'],['#content-valign','middle','options.middle'],['#content-valign','bottom','options.bottom'],['#content-zoom','fit','options.fitWidth'],['#unicode-position','center','options.center'],['#unicode-position','top','options.top'],['#unicode-position','bottom','options.bottom'],['#image-position','center','options.center'],['#image-position','top','options.top'],['#image-position','bottom','options.bottom'],['#watermark-position','center','options.center'],['#watermark-position','top','options.top'],['#watermark-position','bottom','options.bottom']].forEach(entry => setOption(...entry));
    const contentText = document.querySelector('#content-text');
    if (contentText) contentText.placeholder = t('content.textPlaceholder', {}, contentText.placeholder);
    setAttribute('.workspace-nav','aria-label','accessibility.workspace');
    setAttribute('#drop-zone','aria-label','accessibility.dropZone');
    setAttribute('#page-grid','aria-label','accessibility.pages');
    setAttribute('#content-canvas','aria-label','accessibility.preview');
    setAttribute('.content-format','aria-label','accessibility.textFormatting');
    setAttribute('.content-zoom','aria-label','accessibility.previewZoom');
    setAttribute('#back-to-top','aria-label','accessibility.backToTop');
    setAttribute('#back-to-top','title','accessibility.backToTop');
  }
  async function fetchLocale(code) {
    const response = await fetch(`/static/locales/${code}.json`, {credentials: 'same-origin'});
    if (!response.ok) throw new Error('Locale unavailable');
    return response.json();
  }
  async function setLanguage(next) {
    language = languages.includes(next) ? next : 'ko';
    safeSet('pdf-toolkit-language', language);
    root.lang = language;
    try {
      if (!Object.keys(korean).length) korean = await fetchLocale('ko');
      messages = language === 'ko' ? korean : await fetchLocale(language);
    } catch (error) {
      messages = korean;
    }
    applyStatic();
    document.dispatchEvent(new CustomEvent('pdf-toolkit-language-change', {detail: {language}}));
  }
  window.pdfToolkitI18n = {t, translate, getLanguage: () => language, setLanguage, supportedLanguages: languages.slice()};
  window.pdfToolkitTranslate = (key, fallback, params = {}) => t(key, params, fallback);
  document.addEventListener('DOMContentLoaded', () => {
    const themeSelect = document.getElementById('theme-select');
    const languageSelect = document.getElementById('language-select');
    if (themeSelect) {
      themeSelect.value = theme;
      themeSelect.addEventListener('change', () => { const value = themes.includes(themeSelect.value) ? themeSelect.value : 'light'; root.dataset.theme = value; safeSet('pdf-toolkit-theme', value); });
    }
    if (languageSelect) {
      languageSelect.value = language;
      languageSelect.addEventListener('change', () => setLanguage(languageSelect.value));
    }
    setLanguage(language);
  });
})();
