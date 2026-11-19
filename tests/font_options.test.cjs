const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

test("font menus show only validated server choices and preserve upload mode on language change", async () => {
  const handlers = {};
  const makeSelect = () => ({
    value: "default",
    options: [],
    replaceChildren() { this.options = []; },
    append(option) { this.options.push(option); },
    dispatchEvent(event) { this.changed = event.type; }
  });
  const content = makeSelect();
  const watermark = makeSelect();
  const document = {
    querySelector(selector) { return selector === "#content-font-id" ? content : selector === "#unicode-font-id" ? watermark : null; },
    createElement() { return {value: "", textContent: ""}; },
    addEventListener(name, handler) { handlers[name] = handler; }
  };
  const window = {pdfToolkitI18n: {t(key) { return key === "fonts.default" ? "기본 글꼴" : "사용자 글꼴 업로드"; }}};
  const source = fs.readFileSync(path.join(__dirname, "../app/static/js/font-options.js"), "utf8");
  vm.runInNewContext(source, {document, window, Event: class Event { constructor(type) { this.type = type; } }, fetch: async () => ({ok: true, json: async () => ({fonts: [{id: "default", name: "NanumGothic Regular", preview_url: "/api/pdf/fonts/default/file"}]})})});
  await handlers.DOMContentLoaded();
  assert.deepEqual(content.options.map(option => option.value), ["default", "upload"]);
  assert.match(content.options[0].textContent, /NanumGothic Regular/);
  assert.equal(watermark.changed, "change");
  content.value = "upload";
  handlers["pdf-toolkit-language-change"]();
  assert.equal(content.value, "upload");
});
