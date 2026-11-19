const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

function setup(request = null) {
  const elements = {};
  const events = {};
  const windowEvents = {};
  const drawing = {font: "", save() {}, restore() {}, drawImage() {}, fillText() {}, fillRect() {}, strokeRect() {}, translate() {}, rotate() {}, measureText(text) { return {width: [...text].length * (this.font.includes("bold") ? 12 : 10)}; }};
  class Element {
    constructor(id) { this.id = id; this.listeners = {}; this.files = []; this.dataset = {}; this.value = ""; this.checked = false; this.hidden = false; this.style = {}; }
    addEventListener(name, fn) { this.listeners[name] = fn; }
    fire(name, event = {}) { return this.listeners[name]?.({preventDefault() {}, pointerId: 1, clientX: 200, clientY: 200, ...event}); }
    click() { return this.fire("click"); }
    setAttribute() {}
    getContext() { return drawing; }
    getBoundingClientRect() { return {left: 0, top: 0, right: 800, bottom: 1000, width: 800, height: 1000}; }
    setPointerCapture() {}
    focus() { document.activeElement = this; }
    select() {}
    setCustomValidity() {}
    reportValidity() {}
    append() {}
    remove() {}
    matches() { return false; }
  }
  const ids = ["content-file", "content-canvas", "content-zoom", "content-status", "content-page-label", "content-count", "content-text", "content-size", "content-color", "content-font", "content-font-id", "content-font-upload", "content-image", "content-align", "content-valign", "content-leading", "content-bold", "content-italic", "content-image-lock", "content-text-dialog", "content-dialog-form", "content-dialog-value", "content-dialog-title", "content-dialog-submit", "content-dialog-cancel", "content-load", "content-prev", "content-next", "content-undo", "content-redo", "content-save", "content-apply", "content-delete", "content-image-rotate", "content-mode-text", "content-mode-select", "content-mode-image", "content-mode-replace", "content-editor"];
  for (const id of ids) elements[id] = new Element(id);
  elements["content-size"].value = "18";
  elements["content-color"].value = "#000000";
  elements["content-leading"].value = "1.2";
  elements["content-align"].value = "left";
  elements["content-valign"].value = "top";
  elements["content-font-id"].value = "default";
  elements["content-editor"].hidden = false;
  elements["content-text-dialog"].showModal = () => { elements["content-text-dialog"].open = true; };
  elements["content-text-dialog"].close = () => { elements["content-text-dialog"].open = false; };
  const document = {activeElement: null, body: new Element("body"), fonts: {add() {}, delete() {}}, querySelector(selector) { return elements[selector.slice(1)]; }, addEventListener(name, fn) { events[name] = fn; }, createElement() { return new Element("link"); }};
  const context = {document, window: {prompt() { return null; }, confirm() { return true; }, addEventListener(name, fn) { windowEvents[name] = fn; }}, DataTransfer: class { constructor() { this.files = []; this.items = {add: file => this.files.push(file)}; } }, FormData: class { constructor() { this.values = {}; } append(key, value) { this.values[key] = value; } }, FontFace: class { async load() { return this; } }, fetch: request || (() => {}), URL: {createObjectURL() { return "blob:test"; }, revokeObjectURL() {}}, Image: class {}, setTimeout() {}};
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname, "../app/static/js/content-editor.js"), "utf8"), context);
  const run = code => vm.runInContext(code, context);
  const state = () => JSON.parse(run("JSON.stringify({edits:contentEdits,history:contentHistory.length,future:contentFuture.length,selected:contentSelected})"));
  return {elements, events, windowEvents, run, state, document};
}

test("font selection toggles upload input without clearing edits", () => {
  const app = setup();
  app.run("contentEdits=[{type:'text',page:1,x:.1,y:.2,text:'한글',size:18,color:'#000000'}]");
  app.elements["content-font-id"].value = "upload";
  app.elements["content-font-id"].fire("change");
  assert.equal(app.elements["content-font-upload"].hidden, false);
  app.elements["content-font"].value = "selected.ttf";
  app.elements["content-font-id"].value = "default";
  app.elements["content-font-id"].fire("change");
  assert.equal(app.elements["content-font-upload"].hidden, true);
  assert.equal(app.elements["content-font"].value, "");
  assert.equal(app.state().edits.length, 1);
});

test("Unicode multiline auto sizing respects page and manual width", () => {
  const app = setup();
  app.run("contentPages=[{width:400,height:500}]");
  app.run("var sample={type:'text',page:1,x:.75,y:.2,w:.1,h:.05,text:'한글 English 123\\nsecond line',size:18,leading:1.5};contentAutoFit(sample)");
  const first = JSON.parse(app.run("JSON.stringify(sample)"));
  assert.ok(first.w <= .25 && first.h > .05 && first.y >= first.h);
  app.run("sample.manualSize=true;sample.w=.12;sample.text='longer text after manual resize';contentAutoFit(sample)");
  assert.equal(app.run("sample.w"), .12);
  assert.ok(app.run("sample.h") >= first.h);
  assert.equal(JSON.parse(app.run("JSON.stringify(contentWrapText('a\\nb',100))")).length, 2);
});

test("keyboard moves text within baseline bounds and supports undo redo", () => {
  const app = setup();
  app.run("contentPages=[{width:400,height:500}];contentImage={naturalWidth:800,naturalHeight:1000};contentEdits=[{type:'text',page:1,x:.1,y:.3,w:.2,h:.2,text:'Test',size:18,color:'#000000'}];contentSelected=0");
  const key = (name, extra = {}) => app.events.keydown({key: name, preventDefault() {}, ...extra});
  key("ArrowUp", {shiftKey: true});
  assert.ok(Math.abs(app.state().edits[0].y - .28) < 1e-12);
  key("z", {ctrlKey: true});
  assert.equal(app.state().edits[0].y, .3);
  key("z", {ctrlKey: true, shiftKey: true});
  assert.ok(Math.abs(app.state().edits[0].y - .28) < 1e-12);
  app.run("contentSelected=0");
  key("Delete");
  assert.equal(app.state().edits.length, 0);
  key("y", {ctrlKey: true});
  assert.equal(app.state().edits.length, 0);
});

test("keyboard shortcuts leave text entry untouched", () => {
  const app = setup();
  app.run("contentPages=[{width:400,height:500}];contentEdits=[{type:'text',page:1,x:.1,y:.3,w:.2,h:.2,text:'Test',size:18,color:'#000000'}];contentSelected=0");
  app.document.activeElement = {matches() { return true; }};
  app.events.keydown({key: "Delete", preventDefault() {}});
  assert.equal(app.state().edits.length, 1);
  app.document.activeElement = null;
  app.elements["content-text-dialog"].open = true;
  app.events.keydown({key: "Delete", preventDefault() {}});
  assert.equal(app.state().edits.length, 1);
});

test("cancelled drag restores edit without adding history", () => {
  const app = setup();
  app.run("contentPages=[{width:400,height:500}];contentImage={naturalWidth:800,naturalHeight:1000};contentMode='select';contentEdits=[{type:'text',page:1,x:.1,y:.3,w:.2,h:.2,text:'Test',size:18,color:'#000000'}]");
  app.elements["content-canvas"].fire("pointerdown", {clientX: 160, clientY: 200});
  app.elements["content-canvas"].fire("pointermove", {clientX: 240, clientY: 300});
  assert.equal(app.state().history, 1);
  app.elements["content-canvas"].fire("pointercancel");
  assert.equal(app.state().history, 0);
  assert.equal(app.state().edits[0].x, .1);
});

test("stale modal completion after file replacement adds no edit", async () => {
  const app = setup();
  app.run("contentPages=[{width:400,height:500}];contentImage={naturalWidth:800,naturalHeight:1000};contentMode='text'");
  const pending = app.elements["content-canvas"].fire("click");
  assert.equal(app.elements["content-text-dialog"].open, true);
  app.elements["content-file"].fire("change");
  await pending;
  assert.equal(app.state().edits.length, 0);
  assert.equal(app.state().history, 0);
});

test("image movement and rotation remain undoable", () => {
  const app = setup();
  app.run("contentPages=[{width:400,height:500}];contentImage={naturalWidth:800,naturalHeight:1000};contentMode='select';contentEdits=[{type:'image',page:1,x:.1,y:.1,w:.2,h:.2,image:0}];contentSelected=0");
  app.elements["content-canvas"].fire("pointerdown", {clientX: 160, clientY: 200});
  app.elements["content-canvas"].fire("pointermove", {clientX: 240, clientY: 250});
  app.elements["content-canvas"].fire("pointerup", {clientX: 240, clientY: 250});
  assert.ok(app.state().edits[0].x > .1);
  app.elements["content-image-rotate"].click();
  assert.equal(app.state().edits[0].rotation, 90);
  app.elements["content-undo"].click();
  assert.equal(app.state().edits[0].rotation, undefined);
  app.elements["content-undo"].click();
  assert.equal(app.state().edits[0].x, .1);
});

test("all text resize handles are reachable and retain cursor directions", () => {
  const app = setup();
  app.run("contentPages=[{width:400,height:500}];contentImage={naturalWidth:800,naturalHeight:1000};contentMode='select';contentEdits=[{type:'text',page:1,x:.2,y:.5,w:.4,h:.2,text:'Test',size:18,color:'#000000'}];contentSelected=0");
  const points = {nw: [160, 300], n: [320, 300], ne: [480, 300], w: [160, 400], e: [480, 400], sw: [160, 500], s: [320, 500], se: [480, 500]};
  for (const [handle, [clientX, clientY]] of Object.entries(points)) {
    app.elements["content-canvas"].fire("pointerdown", {clientX, clientY});
    assert.equal(app.run("contentDrag.handle"), handle);
    assert.ok(app.elements["content-canvas"].dataset.cursor.includes("resize"));
    app.elements["content-canvas"].fire("pointercancel");
  }
});

test("zoomed canvas point maps to the same normalized PDF position", () => {
  const app = setup();
  const canvas = app.elements["content-canvas"];
  for (const [width, height, left, top] of [[400, 500, 20, 30], [800, 1000, -120, -200], [600, 300, 40, 90], [1200, 1500, 0, -500]]) {
    canvas.getBoundingClientRect = () => ({left, top, width, height});
    const point = JSON.parse(app.run(`JSON.stringify(contentPoint({clientX:${left + width * .25},clientY:${top + height * .4}}))`));
    assert.ok(Math.abs(point.x - .25) < 1e-12);
    assert.ok(Math.abs(point.y - .4) < 1e-12);
  }
});

test("new edits keep unique IDs across undo and a new branch", async () => {
  const app = setup();
  app.run("contentPages=[{width:400,height:500}];contentImage={naturalWidth:800,naturalHeight:1000};contentMode='text'");
  const add = async value => {
    const pending = app.elements["content-canvas"].fire("click");
    app.elements["content-dialog-value"].value = value;
    app.elements["content-dialog-form"].fire("submit");
    await pending;
  };
  await add("First");
  const firstId = app.state().edits[0].id;
  app.elements["content-undo"].click();
  await add("Second");
  assert.notEqual(app.state().edits[0].id, firstId);
  assert.equal(app.state().future, 0);
});

test("proportional image resize can grow and remains within page", () => {
  const app = setup();
  app.run("contentPages=[{width:400,height:500}];contentImage={naturalWidth:800,naturalHeight:1000};contentMode='select';contentEdits=[{id:1,type:'image',page:1,x:.1,y:.1,w:.2,h:.1,image:0}];contentSelected=0");
  app.elements["content-image-lock"].checked = true;
  app.elements["content-canvas"].fire("pointerdown", {clientX: 240, clientY: 200});
  app.elements["content-canvas"].fire("pointermove", {clientX: 320, clientY: 200});
  app.elements["content-canvas"].fire("pointerup", {clientX: 320, clientY: 200});
  const edit = app.state().edits[0];
  assert.ok(edit.w > .2);
  assert.ok(Math.abs(edit.h / edit.w - .5) < 1e-12);
  assert.ok(edit.x + edit.w <= 1 && edit.y + edit.h <= 1);
});

test("page transition cancels a drag and restores the previous edit", () => {
  const app = setup();
  app.run("contentPages=[{width:400,height:500},{width:500,height:400}];contentImage={naturalWidth:800,naturalHeight:1000};contentMode='select';contentEdits=[{id:1,type:'text',page:1,x:.1,y:.3,w:.2,h:.2,text:'Test',size:18,color:'#000000'}];contentSelected=0");
  app.elements["content-canvas"].fire("pointerdown", {clientX: 160, clientY: 200});
  app.elements["content-canvas"].fire("pointermove", {clientX: 240, clientY: 300});
  assert.equal(app.state().history, 1);
  app.elements["content-next"].click();
  assert.equal(app.state().edits[0].x, .1);
  assert.equal(app.state().history, 0);
  assert.equal(app.run("contentDrag"), null);
});

test("save keeps the API edit shape and blocks a duplicate request", async () => {
  const requests = [];
  let finish;
  const app = setup((url, options) => { requests.push({url, body: options.body.values}); return new Promise(resolve => { finish = resolve; }); });
  app.elements["content-file"].files = [{name: "source.pdf"}];
  app.run("contentActiveFile=contentFile.files[0];contentPages=[{width:400,height:500}];contentEdits=[{id:7,manualSize:true,type:'text',page:1,x:.1,y:.3,w:.2,h:.2,text:'Test',size:18,color:'#000000'}]");
  const pending = app.elements["content-save"].click();
  app.elements["content-save"].click();
  assert.equal(requests.length, 1);
  const edits = JSON.parse(requests[0].body.edits);
  assert.equal(edits[0].id, undefined);
  assert.equal(edits[0].manualSize, undefined);
  finish({ok: true, blob: async () => ({})});
  await pending;
});

test("modal grows for multiline text, traps Tab, and restores focus after backdrop cancel", async () => {
  const app = setup();
  const opener = app.elements["content-mode-text"];
  opener.focus();
  const pending = app.run("contentAskText('First\\nSecond', 'Add text')");
  assert.equal(app.elements["content-text-dialog"].open, true);
  assert.equal(app.document.activeElement, app.elements["content-dialog-value"]);
  assert.ok(app.elements["content-dialog-value"].rows >= 5);
  let prevented = false;
  app.elements["content-text-dialog"].fire("keydown", {key: "Tab", shiftKey: true, preventDefault() { prevented = true; }});
  assert.equal(prevented, true);
  assert.equal(app.document.activeElement, app.elements["content-dialog-submit"]);
  app.elements["content-text-dialog"].fire("click", {target: app.elements["content-text-dialog"], clientX: 900, clientY: 1100});
  assert.equal(await pending, null);
  assert.equal(app.document.activeElement, opener);
  assert.equal(app.state().history, 0);
});

test("file replacement cancellation keeps edits and restores active file", () => {
  const app = setup();
  const first = {name: "first.pdf"};
  const second = {name: "second.pdf"};
  app.elements["content-file"].files = [first];
  app.run("contentActiveFile=contentFile.files[0];contentPages=[{width:400,height:500}];contentEdits=[{type:'text',page:1,x:.1,y:.3,w:.2,h:.2,text:'Unsaved',size:18,color:'#000000'}]");
  app.run("window.confirm=()=>false");
  app.elements["content-file"].files = [second];
  app.elements["content-file"].fire("change");
  assert.equal(app.elements["content-file"].files[0], first);
  assert.equal(app.state().edits.length, 1);
  app.run("window.confirm=()=>true");
  app.elements["content-file"].files = [second];
  app.elements["content-file"].fire("change");
  assert.equal(app.state().edits.length, 0);
});

test("beforeunload warns only while edits differ from the saved state", () => {
  const app = setup();
  const event = () => ({preventDefault() { this.prevented = true; }, returnValue: undefined});
  let leave = event();
  app.windowEvents.beforeunload(leave);
  assert.equal(leave.prevented, undefined);
  app.run("contentEdits=[{type:'text',page:1,x:.1,y:.2,text:'Changed'}]");
  leave = event();
  app.windowEvents.beforeunload(leave);
  assert.equal(leave.prevented, true);
  app.run("contentSavedState=JSON.stringify(contentEdits)");
  leave = event();
  app.windowEvents.beforeunload(leave);
  assert.equal(leave.prevented, undefined);
});

test("invalid save is rejected before the request and keeps the edit", () => {
  let calls = 0;
  const app = setup(() => { calls++; return Promise.resolve({ok: true, blob: async () => ({})}); });
  app.elements["content-file"].files = [{name: "source.pdf"}];
  app.run("contentActiveFile=contentFile.files[0];contentPages=[{width:400,height:500}];contentEdits=[{type:'text',page:1,x:.9,y:.3,w:.2,h:.2,text:'Out of bounds',size:18,color:'#000000'}]");
  app.elements["content-save"].click();
  assert.equal(calls, 0);
  assert.equal(app.state().edits.length, 1);
  assert.equal(app.elements["content-status"].dataset.kind, "error");
});

test("save failure preserves edits and allows retry", async () => {
  let calls = 0;
  const app = setup(() => { calls++; return Promise.resolve({ok: false, status: 400, json: async () => ({detail: "Text does not fit."})}); });
  app.elements["content-file"].files = [{name: "source.pdf"}];
  app.run("contentActiveFile=contentFile.files[0];contentPages=[{width:400,height:500}];contentEdits=[{type:'text',page:1,x:.1,y:.3,w:.2,h:.2,text:'Test',size:18,color:'#000000'}]");
  await app.elements["content-save"].click();
  assert.equal(calls, 1);
  assert.equal(app.state().edits.length, 1);
  assert.equal(app.elements["content-status"].textContent, "Text does not fit.");
  await app.elements["content-save"].click();
  assert.equal(calls, 2);
});

test("Escape cancels the modal and Enter remains available for multiline input", async () => {
  const app = setup();
  app.elements["content-mode-text"].focus();
  const pending = app.run("contentAskText('한글\\nEnglish', 'Add text')");
  let prevented = false;
  app.elements["content-text-dialog"].fire("keydown", {key: "Enter", preventDefault() { prevented = true; }});
  assert.equal(prevented, false);
  assert.equal(app.elements["content-text-dialog"].open, true);
  app.elements["content-text-dialog"].fire("cancel");
  assert.equal(await pending, null);
  assert.equal(app.document.activeElement, app.elements["content-mode-text"]);
  assert.equal(app.state().history, 0);
});

test("Command Undo and Redo preserve browser defaults without editor history", () => {
  const app = setup();
  let blocked = false;
  app.events.keydown({key: "z", metaKey: true, preventDefault() { blocked = true; }});
  assert.equal(blocked, false);
  app.run("contentPages=[{width:400,height:500}];contentImage={naturalWidth:800,naturalHeight:1000};contentEdits=[{type:'text',page:1,x:.1,y:.3,w:.2,h:.2,text:'Test',size:18,color:'#000000'}];contentSelected=0");
  app.events.keydown({key: "ArrowRight", preventDefault() {}});
  app.events.keydown({key: "z", metaKey: true, preventDefault() { blocked = true; }});
  assert.equal(app.state().edits[0].x, .1);
  app.events.keydown({key: "z", metaKey: true, shiftKey: true, preventDefault() { blocked = true; }});
  assert.ok(app.state().edits[0].x > .1);
});

test("stale save response cannot replace a new file state", async () => {
  let finish;
  const app = setup(() => new Promise(resolve => { finish = resolve; }));
  app.elements["content-file"].files = [{name: "first.pdf"}];
  app.run("contentActiveFile=contentFile.files[0];contentPages=[{width:400,height:500}];contentEdits=[{type:'text',page:1,x:.1,y:.3,w:.2,h:.2,text:'First',size:18,color:'#000000'}]");
  const pending = app.elements["content-save"].click();
  app.elements["content-file"].files = [{name: "second.pdf"}];
  app.elements["content-file"].fire("change");
  finish({ok: true, blob: async () => ({})});
  await pending;
  assert.equal(app.state().edits.length, 0);
  assert.equal(app.elements["content-status"].textContent, "");
});
