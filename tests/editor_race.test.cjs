const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

class Element {
  constructor() {
    this.children = [];
    this.listeners = {};
    this.files = [];
    this.dataset = {};
    this.disabled = false;
    this.classList = {add() {}, remove() {}};
    this.textContent = "";
  }
  addEventListener(name, handler) { this.listeners[name] = handler; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = [...items]; }
  setAttribute() {}
  remove() {}
  click() { return this.listeners.click?.({preventDefault() {}}); }
  fire(name, event = {}) { return this.listeners[name]?.({preventDefault() {}, ...event}); }
}

function setup({deferSave = false} = {}) {
  const ids = ["editor-file", "page-grid", "editor-status", "editor-load", "editor-select-all", "editor-rotate", "editor-delete", "editor-save", "editor-undo"];
  const elements = Object.fromEntries(ids.map(id => [id, new Element()]));
  const pending = [];
  const saved = [];
  let urlNumber = 0;
  const context = {
    document: {
      querySelector(selector) { return elements[selector.slice(1)]; },
      getElementById(id) { return elements[id]; },
      createElement() { return new Element(); },
      createTextNode(text) { return {textContent: text}; },
      body: new Element()
    },
    window: {confirm() { return true; }, addEventListener() {}},
    URL: {
      createObjectURL(blob) { return `blob:${blob.file || "output"}:${blob.page || ++urlNumber}`; },
      revokeObjectURL() {}
    },
    FormData: class {
      constructor() { this.values = {}; }
      append(key, value) { this.values[key] = value; }
    },
    fetch(url, options) {
      const endpoint = url.split("/").at(-1);
      if (endpoint === "organize") {
        saved.push({file: options.body.values.file.name, operations: JSON.parse(options.body.values.operations)});
        if (deferSave) return new Promise((resolve, reject) => pending.push({endpoint, file: options.body.values.file.name, resolve, reject}));
        return Promise.resolve({ok: true, blob: async () => ({})});
      }
      return new Promise((resolve, reject) => pending.push({endpoint, file: options.body.values.file.name, page: options.body.values.page, resolve, reject}));
    },
    setTimeout() {}
  };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname, "../app/static/js/editor.js"), "utf8"), context);
  const snapshot = () => JSON.parse(vm.runInContext("JSON.stringify({pages:editorPages.map(({page,rotation,selected,url})=>({page,rotation,selected,url})), history:editorHistory.length, working:editorWorking, dirty:editorDirty})", context));
  const flush = async () => { for (let i = 0; i < 8; i++) await Promise.resolve(); };
  const request = (file, endpoint) => {
    const index = pending.findIndex(item => item.file === file && item.endpoint === endpoint);
    assert.notEqual(index, -1, `Missing ${file} ${endpoint}`);
    return pending.splice(index, 1)[0];
  };
  const choose = name => { elements["editor-file"].files = [{name}]; elements["editor-file"].fire("change"); };
  const load = () => elements["editor-load"].click();
  const completeInfo = async (name, outcome = "success") => {
    const item = request(name, "info");
    if (outcome === "failure") item.reject(new Error(`${name} failed`));
    else item.resolve({ok: true, json: async () => ({page_count: 2})});
    await flush();
  };
  const completeThumbnail = async (name, outcome = "success") => {
    const item = request(name, "thumbnail");
    if (outcome === "failure") item.reject(new Error(`${name} thumbnail failed`));
    else item.resolve({ok: true, blob: async () => ({file: name, page: item.page})});
    await flush();
  };
  const complete = async (name, outcome = "success") => {
    await completeInfo(name, outcome);
    if (outcome === "success" && pending.some(item => item.file === name && item.endpoint === "thumbnail")) {
      await completeThumbnail(name);
      await completeThumbnail(name);
    }
  };
  const card = index => elements["page-grid"].children[index];
  const select = index => {
    const checkbox = card(index).children[1].children[0];
    checkbox.checked = true;
    checkbox.fire("change");
  };
  const deselect = index => {
    const checkbox = card(index).children[1].children[0];
    checkbox.checked = false;
    checkbox.fire("change");
  };
  return {elements, saved, pending, snapshot, flush, choose, load, complete, completeInfo, completeThumbnail, card, select, deselect};
}

for (const [order, aOutcome, bOutcome] of [
  ["AB", "success", "success"],
  ["BA", "success", "success"],
  ["AB", "failure", "success"],
  ["BA", "failure", "success"],
  ["AB", "success", "failure"],
  ["BA", "success", "failure"]
]) {
  test(`load order ${order}, A ${aOutcome}, B ${bOutcome}`, async () => {
    const app = setup();
    app.choose("A.pdf");
    const a = app.load();
    app.choose("B.pdf");
    const b = app.load();
    for (const name of order) {
      await app.complete(name === "A" ? "A.pdf" : "B.pdf", name === "A" ? aOutcome : bOutcome);
      if (name === "A" && order === "AB") {
        assert.equal(app.snapshot().working, true);
        assert.equal(app.elements["editor-save"].disabled, true);
        assert.equal(app.elements["editor-undo"].disabled, true);
        assert.equal(app.elements["editor-status"].textContent, "Loading pages...");
      }
    }
    await Promise.all([a, b]);
    const state = app.snapshot();
    assert.equal(state.working, false);
    assert.equal(state.history, 0);
    if (bOutcome === "success") {
      assert.deepEqual(state.pages.map(item => item.url), ["blob:B.pdf:1", "blob:B.pdf:2"]);
      assert.equal(app.elements["editor-save"].disabled, false);
      assert.equal(app.elements["editor-undo"].disabled, true);
      assert.equal(app.elements["editor-status"].textContent, "2 pages loaded. Drag or use arrows to reorder.");
      app.select(0);
      app.elements["editor-rotate"].click();
      assert.equal(app.elements["editor-undo"].disabled, false);
      app.elements["editor-save"].click();
      await app.flush();
      assert.deepEqual(app.saved[0], {file: "B.pdf", operations: [{page: 1, rotation: 90}, {page: 2, rotation: 0}]});
    } else {
      assert.deepEqual(state.pages, []);
      assert.equal(app.elements["editor-save"].disabled, true);
      assert.equal(app.elements["editor-status"].textContent, "Connection failed. Check the server and try again.");
    }
  });
}

test("stale thumbnail response cannot appear after a new file starts", async () => {
  const app = setup();
  app.choose("A.pdf");
  const a = app.load();
  await app.completeInfo("A.pdf");
  app.choose("B.pdf");
  const b = app.load();
  await app.completeThumbnail("A.pdf");
  assert.equal(app.snapshot().working, true);
  assert.deepEqual(app.snapshot().pages, []);
  await app.complete("B.pdf");
  await Promise.all([a, b]);
  assert.deepEqual(app.snapshot().pages.map(item => item.url), ["blob:B.pdf:1", "blob:B.pdf:2"]);
});

test("stale thumbnail failure cannot replace the latest error", async () => {
  const app = setup();
  app.choose("A.pdf");
  const a = app.load();
  await app.completeInfo("A.pdf");
  app.choose("B.pdf");
  const b = app.load();
  await app.complete("B.pdf", "failure");
  await app.completeThumbnail("A.pdf", "failure");
  await Promise.all([a, b]);
  assert.equal(app.elements["editor-status"].textContent, "Connection failed. Check the server and try again.");
  assert.deepEqual(app.snapshot().pages, []);
});

test("rapid three-file selection retains only the latest file", async () => {
  const app = setup();
  app.choose("A.pdf");
  const a = app.load();
  app.choose("B.pdf");
  const b = app.load();
  app.choose("C.pdf");
  const c = app.load();
  await app.complete("C.pdf");
  await app.complete("A.pdf");
  await app.complete("B.pdf", "failure");
  await Promise.all([a, b, c]);
  assert.deepEqual(app.snapshot().pages.map(item => item.url), ["blob:C.pdf:1", "blob:C.pdf:2"]);
  assert.equal(app.elements["editor-status"].textContent, "2 pages loaded. Drag or use arrows to reorder.");
});

test("selection, reorder, delete, undo, and save remain available", async () => {
  const app = setup();
  app.choose("B.pdf");
  const load = app.load();
  await app.complete("B.pdf");
  await load;
  app.select(0);
  app.elements["editor-rotate"].click();
  app.card(0).children[2].children[1].click();
  assert.deepEqual(app.snapshot().pages.map(item => item.page), [2, 1]);
  app.deselect(1);
  app.select(0);
  app.elements["editor-delete"].click();
  assert.deepEqual(app.snapshot().pages.map(item => item.page), [1]);
  app.elements["editor-undo"].click();
  assert.deepEqual(app.snapshot().pages.map(item => item.page), [2, 1]);
  app.elements["editor-undo"].click();
  assert.deepEqual(app.snapshot().pages.map(item => item.page), [1, 2]);
  app.elements["editor-undo"].click();
  assert.deepEqual(app.snapshot().pages.map(item => item.rotation), [0, 0]);
  assert.equal(app.elements["editor-undo"].disabled, true);
  app.select(0);
  app.elements["editor-rotate"].click();
  app.elements["editor-save"].click();
  await app.flush();
  assert.deepEqual(app.saved[0].operations, [{page: 1, rotation: 90}, {page: 2, rotation: 0}]);
});

test("stale save completion cannot unlock or overwrite a new load", async () => {
  const app = setup({deferSave: true});
  app.choose("A.pdf");
  const firstLoad = app.load();
  await app.complete("A.pdf");
  await firstLoad;
  app.select(0);
  app.elements["editor-rotate"].click();
  const oldSave = app.elements["editor-save"].click();
  app.choose("B.pdf");
  const newLoad = app.load();
  const pendingSave = app.pending.splice(app.pending.findIndex(item => item.endpoint === "organize"), 1)[0];
  pendingSave.resolve({ok: true, blob: async () => ({})});
  await oldSave;
  assert.equal(app.snapshot().working, true);
  assert.equal(app.elements["editor-save"].disabled, true);
  assert.equal(app.elements["editor-status"].textContent, "Loading pages...");
  await app.complete("B.pdf");
  await newLoad;
  assert.deepEqual(app.snapshot().pages.map(item => item.url), ["blob:B.pdf:1", "blob:B.pdf:2"]);
  assert.equal(app.elements["editor-undo"].disabled, true);
});
