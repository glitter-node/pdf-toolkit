const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../app/static/js/preferences.js'), 'utf8');

function setup(storedLanguage = null) {
  const values = new Map();
  if (storedLanguage !== null) values.set('pdf-toolkit-language', storedLanguage);
  const handlers = {};
  const elements = {
    'theme-select': {value: '', addEventListener(type, handler) { this[type] = handler; }},
    'language-select': {value: '', addEventListener(type, handler) { this[type] = handler; }}
  };
  const document = {
    documentElement: {dataset: {}, lang: ''},
    addEventListener(type, handler) { handlers[type] = handler; },
    getElementById(id) { return elements[id] || null; },
    querySelector() { return null; },
    dispatchEvent(event) { this.lastEvent = event; }
  };
  const localStorage = {getItem(key) { return values.get(key) ?? null; }, setItem(key, value) { values.set(key, value); }};
  const context = {
    window: {localStorage}, document, Intl, console,
    CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options.detail; } },
    fetch: async url => ({ok: true, json: async () => JSON.parse(fs.readFileSync(path.join(__dirname, `../app${url}`), 'utf8'))})
  };
  vm.createContext(context);
  vm.runInContext(source, context);
  handlers.DOMContentLoaded();
  return {context, document, elements, values};
}

test('invalid stored language falls back to Korean and supports interpolation', async () => {
  const state = setup('invalid');
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(state.document.documentElement.lang, 'ko');
  assert.equal(state.values.get('pdf-toolkit-language'), 'ko');
  assert.equal(state.context.window.pdfToolkitI18n.t('content.pagePosition', {current: 2, total: 5}), '2/5페이지');
});

test('language changes preserve application state and use Korean fallback', async () => {
  const state = setup('ko');
  await new Promise(resolve => setImmediate(resolve));
  const editorState = {page: 3, history: ['edit']};
  await state.context.window.pdfToolkitI18n.setLanguage('ja');
  assert.equal(state.document.documentElement.lang, 'ja');
  assert.equal(state.context.window.pdfToolkitI18n.t('tools.merge'), 'PDFを結合');
  assert.deepEqual(editorState, {page: 3, history: ['edit']});
  assert.equal(state.document.lastEvent.type, 'pdf-toolkit-language-change');
});
