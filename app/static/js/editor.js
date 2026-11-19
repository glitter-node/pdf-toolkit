const editorFile = document.querySelector("#editor-file");
const editorT = (key, params = {}, fallback = "") => window.pdfToolkitI18n?.t(key, params, fallback) || fallback;
const editorTranslate = value => window.pdfToolkitI18n?.translate(value) || value;
const editorGrid = document.querySelector("#page-grid");
const editorStatus = document.querySelector("#editor-status");
const editorButtons = ["editor-load", "editor-select-all", "editor-rotate", "editor-delete", "editor-save", "editor-undo"];
let editorPages = [];
let editorUrls = [];
let editorHistory = [];
let draggedPage = null;
let editorWorking = false;
let editorGeneration = 0;
let editorDirty = false;
function editorMessage(message, kind = "info") {
  editorStatus.textContent = editorTranslate(message);
  editorStatus.dataset.kind = kind;
}
function editorBusy(value) {
  editorWorking = value;
  for (const id of editorButtons) document.getElementById(id).disabled = value;
  if (!value) editorControls();
}
function editorControls() {
  if (editorWorking) return;
  document.getElementById("editor-load").disabled = !editorFile.files.length;
  document.getElementById("editor-select-all").disabled = !editorPages.length;
  document.getElementById("editor-rotate").disabled = !editorPages.some(item => item.selected);
  document.getElementById("editor-delete").disabled = !editorPages.some(item => item.selected);
  document.getElementById("editor-save").disabled = !editorPages.length;
  document.getElementById("editor-undo").disabled = !editorHistory.length;
}
function clearEditor() {
  editorGeneration++;
  editorWorking = false;
  for (const url of editorUrls) URL.revokeObjectURL(url);
  editorUrls = [];
  editorPages = [];
  editorHistory = [];
  editorDirty = false;
  editorGrid.replaceChildren();
  editorControls();
}
function editorSnapshot() {
  editorHistory.push(editorPages.map(item => ({...item})));
  if (editorHistory.length > 30) editorHistory.shift();
  editorDirty = true;
}
async function editorRequest(endpoint, extra = {}, signal, file = editorFile.files[0]) {
  if (!file) throw new Error("Select a PDF first.");
  const data = new FormData();
  data.append("file", file);
  for (const [key, value] of Object.entries(extra)) data.append(key, value);
  let response;
  try {
    response = await fetch(`/api/pdf/${endpoint}`, {method: "POST", body: data, signal});
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error("Connection failed. Check the server and try again.");
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = payload.detail;
    throw new Error(typeof detail === "string" ? detail : `PDF request failed (HTTP ${response.status}).`);
  }
  return response;
}
function editorMove(item, direction) {
  const index = editorPages.indexOf(item);
  const next = index + direction;
  if (next < 0 || next >= editorPages.length) return;
  editorSnapshot();
  [editorPages[index], editorPages[next]] = [editorPages[next], editorPages[index]];
  drawEditor();
  editorMessage("Page order changed. Save to export.");
}
function drawEditor() {
  editorGrid.replaceChildren();
  for (const [index, item] of editorPages.entries()) {
    const card = document.createElement("div");
    card.className = `page-card${item.selected ? " selected" : ""}`;
    card.draggable = true;
    const img = document.createElement("img");
    img.src = item.url;
    img.alt = editorT("pageEditor.previewAlt", {page: item.page}, `Page ${item.page} preview`);
    img.className = `rotation-${item.rotation}`;
    const label = document.createElement("label");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = item.selected;
    checkbox.addEventListener("change", () => { item.selected = checkbox.checked; drawEditor(); });
    label.append(checkbox, document.createTextNode(editorT("pageEditor.pageLabel", {page: item.page, rotation: item.rotation}, `Page ${item.page} (${item.rotation}°)`)));
    const moves = document.createElement("div");
    moves.className = "page-moves";
    for (const [direction, text] of [[-1, "Move left"], [1, "Move right"]]) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = direction < 0 ? "←" : "→";
      const moveLabel = editorT(direction < 0 ? "pageEditor.moveLeft" : "pageEditor.moveRight", {page: item.page}, `${text}: page ${item.page}`);
      button.setAttribute("aria-label", moveLabel);
      button.title = moveLabel;
      button.disabled = editorWorking || index + direction < 0 || index + direction >= editorPages.length;
      button.addEventListener("click", () => editorMove(item, direction));
      moves.append(button);
    }
    card.append(img, label, moves);
    card.addEventListener("dragstart", () => { draggedPage = item; card.classList.add("dragging"); });
    card.addEventListener("dragend", () => { draggedPage = null; card.classList.remove("dragging"); });
    card.addEventListener("dragover", event => event.preventDefault());
    card.addEventListener("drop", event => {
      event.preventDefault();
      if (!draggedPage || draggedPage === item) return;
      editorSnapshot();
      editorPages.splice(editorPages.indexOf(draggedPage), 1);
      editorPages.splice(editorPages.indexOf(item), 0, draggedPage);
      drawEditor();
      editorMessage("Page order changed. Save to export.");
    });
    editorGrid.append(card);
  }
  editorControls();
}
document.querySelector("#editor-load").addEventListener("click", async () => {
  if (!editorFile.files.length) { editorMessage("Select a PDF first.", "error"); return; }
  if (editorDirty && !window.confirm(editorT("pageEditor.discard", {}, "Discard unsaved page edits?"))) return;
  clearEditor();
  const generation = editorGeneration;
  const file = editorFile.files[0];
  editorBusy(true);
  editorMessage("Loading pages...", "working");
  try {
    const response = await editorRequest("info", {}, undefined, file);
    if (generation !== editorGeneration) return;
    const info = await response.json();
    if (generation !== editorGeneration) return;
    if (!Number.isInteger(info.page_count) || info.page_count < 1) throw new Error("PDF contains no editable pages.");
    for (let page = 1; page <= info.page_count; page++) {
      const thumbnail = await editorRequest("thumbnail", {page}, undefined, file);
      if (generation !== editorGeneration) return;
      const blob = await thumbnail.blob();
      if (generation !== editorGeneration) return;
      const url = URL.createObjectURL(blob);
      if (generation !== editorGeneration) { URL.revokeObjectURL(url); return; }
      editorUrls.push(url);
      editorPages.push({page, rotation: 0, selected: false, url});
      drawEditor();
      editorMessage(editorT("pageEditor.loadingProgress", {current: page, total: info.page_count}, `Loading pages ${page}/${info.page_count}...`), "working");
    }
    if (generation === editorGeneration) editorMessage(editorT("pageEditor.loaded", {count: editorPages.length}, `${editorPages.length} pages loaded. Drag or use arrows to reorder.`), "success");
  } catch (error) {
    if (generation === editorGeneration) { clearEditor(); editorMessage(error.message, "error"); }
  } finally { if (generation === editorGeneration) editorBusy(false); }
});
document.querySelector("#editor-select-all").addEventListener("click", () => {
  const select = editorPages.some(item => !item.selected);
  for (const item of editorPages) item.selected = select;
  drawEditor();
});
document.querySelector("#editor-rotate").addEventListener("click", () => {
  if (!editorPages.some(item => item.selected)) return;
  editorSnapshot();
  for (const item of editorPages) if (item.selected) item.rotation = (item.rotation + 90) % 360;
  drawEditor();
  editorMessage("Selected pages rotated. Save to export.");
});
document.querySelector("#editor-delete").addEventListener("click", () => {
  if (!editorPages.some(item => item.selected)) return;
  if (editorPages.every(item => item.selected)) { editorMessage("At least one page must remain.", "error"); return; }
  editorSnapshot();
  editorPages = editorPages.filter(item => !item.selected);
  drawEditor();
  editorMessage(editorT("pageEditor.remaining", {count: editorPages.length}, `${editorPages.length} pages remain. Save to export.`));
});
document.querySelector("#editor-undo").addEventListener("click", () => {
  if (!editorHistory.length) return;
  editorPages = editorHistory.pop();
  editorDirty = editorHistory.length > 0;
  drawEditor();
  editorMessage("Last edit undone.");
});
document.querySelector("#editor-save").addEventListener("click", async () => {
  if (!editorPages.length) { editorMessage("No pages to save.", "error"); return; }
  const generation = editorGeneration;
  const file = editorFile.files[0];
  editorBusy(true);
  editorMessage("Saving...", "working");
  try {
    const operations = JSON.stringify(editorPages.map(item => ({page: item.page, rotation: item.rotation})));
    const response = await editorRequest("organize", {operations}, undefined, file);
    if (generation !== editorGeneration) return;
    const blob = await response.blob();
    if (generation !== editorGeneration) return;
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "organized.pdf";
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
    editorDirty = false;
    editorHistory = [];
    editorMessage("PDF saved successfully.", "success");
  } catch (error) { if (generation === editorGeneration) editorMessage(error.message, "error"); }
  finally { if (generation === editorGeneration) editorBusy(false); }
});
editorFile.addEventListener("change", () => { clearEditor(); editorMessage(""); });
if (document.addEventListener) document.addEventListener("pdf-toolkit-language-change", () => { if (editorPages.length) drawEditor(); });
window.addEventListener("pagehide", clearEditor);
