const contentFile = document.querySelector("#content-file");
const contentT = (key, params = {}, fallback = "") => window.pdfToolkitI18n?.t(key, params, fallback) || fallback;
const contentTranslate = value => window.pdfToolkitI18n?.translate(value) || value;
const contentCanvas = document.querySelector("#content-canvas");
const contentContext = contentCanvas.getContext("2d");
const contentZoom = document.querySelector("#content-zoom");
const contentStatus = document.querySelector("#content-status");
const contentPageLabel = document.querySelector("#content-page-label");
const contentCount = document.querySelector("#content-count");
const contentText = document.querySelector("#content-text");
const contentSize = document.querySelector("#content-size");
const contentColor = document.querySelector("#content-color");
const contentFont = document.querySelector("#content-font");
const contentFontId = document.querySelector("#content-font-id");
const contentFontUpload = document.querySelector("#content-font-upload");
const contentImageFile = document.querySelector("#content-image");
const contentAlign = document.querySelector("#content-align");
const contentVAlign = document.querySelector("#content-valign");
const contentLeading = document.querySelector("#content-leading");
const contentBold = document.querySelector("#content-bold");
const contentItalic = document.querySelector("#content-italic");
const contentImageLock = document.querySelector("#content-image-lock");
const contentTextDialog = document.querySelector("#content-text-dialog");
const contentDialogForm = document.querySelector("#content-dialog-form");
const contentDialogValue = document.querySelector("#content-dialog-value");
const contentDialogTitle = document.querySelector("#content-dialog-title");
const contentDialogSubmit = document.querySelector("#content-dialog-submit");
const contentDialogCancel = document.querySelector("#content-dialog-cancel");
let contentDialogResolve = null;
let contentDialogFocus = null;
let contentPreviewFont = null;
let contentPreviewFontUrl = null;
function contentSizeDialogInput() {
  contentDialogValue.rows = Math.min(12, Math.max(5, contentDialogValue.value.split("\n").length + Math.floor(contentDialogValue.value.length / 55)));
}
function contentAskText(initial, title) {
  const translatedTitle = contentTranslate(title);
  if (!contentTextDialog || typeof contentTextDialog.showModal !== "function") return Promise.resolve(window.prompt(translatedTitle, initial));
  if (contentTextDialog.open) return Promise.resolve(null);
  contentDialogTitle.textContent = translatedTitle;
  contentDialogSubmit.textContent = title === "Add text" ? contentT("modal.add", {}, "Add text") : contentT("modal.update", {}, "Update text");
  contentDialogSubmit.disabled = false;
  contentDialogValue.value = initial;
  contentSizeDialogInput();
  return new Promise(resolve => {
    contentDialogResolve = resolve;
    contentDialogFocus = document.activeElement;
    contentTextDialog.showModal();
    contentDialogValue.focus();
    contentDialogValue.select();
  });
}
function contentCloseTextDialog(value) {
  if (!contentDialogResolve) return;
  const resolve = contentDialogResolve;
  contentDialogResolve = null;
  contentDialogSubmit.disabled = true;
  if (contentTextDialog.open) contentTextDialog.close();
  if (contentDialogFocus?.focus) contentDialogFocus.focus();
  contentDialogFocus = null;
  resolve(value);
}
if (contentTextDialog) {
  contentDialogForm.addEventListener("submit", event => {
    event.preventDefault();
    if (!contentDialogValue.value.trim()) {
      contentDialogValue.setCustomValidity(contentT("content.enterText", {}, "Enter text to add."));
      contentDialogValue.reportValidity();
      return;
    }
    contentDialogValue.setCustomValidity("");
    contentCloseTextDialog(contentDialogValue.value);
  });
  contentDialogValue.addEventListener("input", () => { contentDialogValue.setCustomValidity(""); contentSizeDialogInput(); });
  contentDialogCancel.addEventListener("click", () => contentCloseTextDialog(null));
  contentTextDialog.addEventListener("cancel", event => { event.preventDefault(); contentCloseTextDialog(null); });
  contentTextDialog.addEventListener("click", event => {
    if (event.target !== contentTextDialog) return;
    const rect = contentTextDialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) contentCloseTextDialog(null);
  });
  contentTextDialog.addEventListener("keydown", event => {
    if (event.key !== "Tab") return;
    const first = contentDialogValue;
    const last = contentDialogSubmit;
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
}
let contentPages = [];
let contentIndex = 0;
let contentEdits = [];
let contentHistory = [];
let contentFuture = [];
let contentImages = [];
let contentGeneration = 0;
let contentWorking = false;
let contentImage = null;
let contentMode = "text";
let contentSelected = -1;
let contentDrag = null;
let contentNextId = 1;
let contentActiveFile = null;
let contentSavedState = "[]";
function contentIsDirty() {
  return JSON.stringify(contentEdits) !== contentSavedState;
}
function contentNewId() {
  return contentNextId++;
}
function contentMessage(message, kind = "info") {
  contentStatus.textContent = contentTranslate(message);
  contentStatus.dataset.kind = kind;
}
function contentControls() {
  const loaded = contentPages.length > 0;
  document.querySelector("#content-load").disabled = contentWorking || !contentFile.files.length;
  document.querySelector("#content-prev").disabled = contentWorking || !loaded || contentIndex === 0;
  document.querySelector("#content-next").disabled = contentWorking || !loaded || contentIndex === contentPages.length - 1;
  document.querySelector("#content-undo").disabled = contentWorking || !contentHistory.length;
  document.querySelector("#content-redo").disabled = contentWorking || !contentFuture.length;
  document.querySelector("#content-save").disabled = contentWorking || !contentEdits.length;
  document.querySelector("#content-apply").disabled = contentWorking || contentSelected < 0 || !["text", "replace"].includes(contentEdits[contentSelected]?.type || "text");
  document.querySelector("#content-delete").disabled = contentWorking || contentSelected < 0;
  document.querySelector("#content-image-rotate").disabled = contentWorking || contentEdits[contentSelected]?.type !== "image";
  contentCount.textContent = contentT("content.editCount", {count: contentEdits.length}, `${contentEdits.length} content edits`);
  contentPageLabel.textContent = loaded ? contentT("content.pagePosition", {current: contentIndex + 1, total: contentPages.length}, `Page ${contentIndex + 1} of ${contentPages.length}`) : contentT("content.noDocument", {}, "No document loaded");
  for (const mode of ["text", "select", "image", "replace"]) {
    const button = document.querySelector(`#content-mode-${mode}`);
    button.disabled = contentWorking;
    button.setAttribute("aria-pressed", String(mode === contentMode));
  }
}
function contentSnapshot() {
  contentHistory.push(JSON.stringify(contentEdits));
  if (contentHistory.length > 50) contentHistory.shift();
  contentFuture = [];
}
function contentCancelDrag() {
  if (contentDrag?.changed) {
    contentEdits = JSON.parse(contentDrag.before);
    contentHistory.pop();
    contentFuture = contentDrag.future;
  }
  contentDrag = null;
}
function contentReset() {
  contentGeneration++;
  contentCloseTextDialog(null);
  contentDrag = null;
  contentWorking = false;
  contentPages = [];
  contentEdits = [];
  contentHistory = [];
  contentFuture = [];
  contentImages = [];
  contentIndex = 0;
  contentSelected = -1;
  contentNextId = 1;
  contentActiveFile = null;
  contentSavedState = "[]";
  contentImage = null;
  contentCanvas.width = 0;
  contentCanvas.height = 0;
  contentMessage("");
  contentControls();
}
async function contentUpdateFont() {
  if (contentPreviewFontUrl) URL.revokeObjectURL(contentPreviewFontUrl);
  if (contentPreviewFont) document.fonts.delete(contentPreviewFont);
  contentPreviewFontUrl = null;
  contentPreviewFont = null;
  const file = contentFontId.value === "upload" ? contentFont.files[0] : null;
  if (contentFontId.value === "upload" && !file) { contentDraw(); return; }
  if (file && (!/\.(ttf|otf)$/i.test(file.name) || file.size > 10_000_000)) return contentMessage("Choose a TTF or OTF font under 10 MB.", "error");
  const url = file ? URL.createObjectURL(file) : `/api/fonts/${contentFontId.value}`;
  contentPreviewFontUrl = url;
  try {
    const weight = contentFontId.value === "default" ? "100" : contentFontId.value === "noto-serif-kr" ? "200" : "400";
    const font = new FontFace("ContentEditorFont", `url(${url})`, {weight});
    await font.load();
    if (contentPreviewFontUrl !== url) return;
    document.fonts.add(font);
    contentPreviewFont = font;
    contentDraw();
  } catch {
    if (contentPreviewFontUrl === url) contentMessage("Unable to preview the selected font.", "error");
  }
}
contentFont.addEventListener("change", contentUpdateFont);
contentFontId.addEventListener("change", () => {
  contentFontUpload.hidden = contentFontId.value !== "upload";
  if (contentFontUpload.hidden) contentFont.value = "";
  contentUpdateFont();
});
contentUpdateFont();
async function contentRequest(endpoint, extra, file, attachments = false) {
  const form = new FormData();
  form.append("file", file);
  for (const [key, value] of Object.entries(extra)) form.append(key, value);
  if (attachments) {
    if (contentFontId.value === "upload" && contentFont.files.length) form.append("font", contentFont.files[0]);
    for (const item of contentImages) form.append("images", item.file);
  }
  let response;
  try {
    response = await fetch(`/api/pdf/${endpoint}`, {method: "POST", body: form});
  } catch {
    throw new Error("Connection failed. Check the server and try again.");
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(typeof payload.detail === "string" ? payload.detail : `PDF request failed (HTTP ${response.status}).`);
  }
  return response;
}
function contentApplyZoom() {
  const zoom = contentZoom.value;
  contentCanvas.className = zoom === "fit" ? "" : `content-zoom-${zoom}`;
}
contentZoom.addEventListener("change", contentApplyZoom);
contentApplyZoom();
function contentDraw() {
  if (!contentImage) return;
  contentCanvas.width = contentImage.naturalWidth;
  contentCanvas.height = contentImage.naturalHeight;
  contentContext.drawImage(contentImage, 0, 0);
  const page = contentPages[contentIndex];
  contentEdits.forEach((edit, index) => {
    if (edit.page !== contentIndex + 1) return;
    const x = edit.x * contentCanvas.width;
    const y = edit.y * contentCanvas.height;
    const scale = contentCanvas.width / page.width;
    if (edit.type === "image") {
      const asset = contentImages[edit.image];
      if (asset?.preview?.complete) {
        const width = edit.w * contentCanvas.width;
        const height = edit.h * contentCanvas.height;
        contentContext.save();
        contentContext.translate(x + width / 2, y + height / 2);
        contentContext.rotate((edit.rotation || 0) * Math.PI / 180);
        const quarter = (edit.rotation || 0) % 180 !== 0;
        contentContext.drawImage(asset.preview, -(quarter ? height : width) / 2, -(quarter ? width : height) / 2, quarter ? height : width, quarter ? width : height);
        contentContext.restore();
      }
    } else if (edit.type === "replace") {
      contentContext.fillStyle = "#ffffff";
      contentContext.fillRect(x, y, edit.w * contentCanvas.width, edit.h * contentCanvas.height);
      contentContext.strokeStyle = "#b54c4c";
      contentContext.strokeRect(x, y, edit.w * contentCanvas.width, edit.h * contentCanvas.height);
      if (edit.text) contentDrawText(edit, x, y + Math.min(edit.h * contentCanvas.height, edit.size * scale * 1.2), scale);
    } else {
      contentDrawText(edit, x, y, scale);
    }
    if (index === contentSelected) {
      contentContext.strokeStyle = "#1463d8";
      contentContext.lineWidth = 3;
      const width = edit.w ? edit.w * contentCanvas.width : Math.max(20, edit.text.length * edit.size * scale * 0.55);
      const height = edit.h ? edit.h * contentCanvas.height : edit.size * scale * 1.3;
      const top = edit.type === "text" ? y - height : y;
      contentContext.strokeRect(x, top, width, height);
      if (edit.type === "text") {
        contentContext.fillStyle = "#ffffff";
        contentContext.strokeStyle = "#1463d8";
        for (const [hx, hy] of [[x, top], [x + width / 2, top], [x + width, top], [x, top + height / 2], [x + width, top + height / 2], [x, top + height], [x + width / 2, top + height], [x + width, top + height]]) {
          contentContext.fillRect(hx - 5, hy - 5, 10, 10);
          contentContext.strokeRect(hx - 5, hy - 5, 10, 10);
        }
      }
      contentContext.lineWidth = 1;
    }
  });
}
function contentDrawText(edit, x, y, scale) {
  contentContext.font = `${edit.italic ? "italic " : ""}${edit.bold ? "bold " : ""}${edit.size * scale}px ${contentPreviewFont && !edit.bold && !edit.italic ? "ContentEditorFont" : "Arial, sans-serif"}`;
  contentContext.fillStyle = edit.color;
  if (edit.type === "text" && edit.w && edit.h) {
    const width = edit.w * contentCanvas.width;
    const top = y - edit.h * contentCanvas.height;
    const lineHeight = edit.size * scale * (edit.leading || 1.2);
    const lines = contentWrapText(edit.text, width);
    const height = edit.h * contentCanvas.height;
    const textHeight = lines.length * lineHeight;
    const vertical = edit.valign || "middle";
    const offset = vertical === "top" ? 0 : vertical === "bottom" ? Math.max(0, height - textHeight) : Math.max(0, (height - textHeight) / 2);
    const firstBaseline = top + offset + lineHeight * 0.85;
    const alignment = edit.align || "center";
    contentContext.textAlign = alignment;
    for (let i = 0; i < lines.length; i++) {
      const baseline = firstBaseline + i * lineHeight;
      if (baseline <= y + 0.01) contentContext.fillText(lines[i], alignment === "left" ? x : alignment === "right" ? x + width : x + width / 2, baseline);
    }
    contentContext.textAlign = "left";
  } else contentContext.fillText(edit.text, x, y);
}
function contentWrapText(text, width) {
  const lines = [];
  for (const paragraph of text.split("\n")) {
    let line = "";
    for (const char of paragraph) {
      const candidate = line + char;
      if (line && contentContext.measureText(candidate).width > width) {
        lines.push(line);
        line = char;
      } else line = candidate;
    }
    lines.push(line);
  }
  return lines;
}
function contentTextHandle(point, edit) {
  if (edit.type !== "text" || !edit.w || !edit.h) return null;
  const x0 = edit.x;
  const x1 = edit.x + edit.w;
  const y0 = edit.y - edit.h;
  const y1 = edit.y;
  const tolerance = (window.matchMedia?.("(pointer: coarse)").matches ? 14 : 9) / Math.min(contentCanvas.getBoundingClientRect().width, contentCanvas.getBoundingClientRect().height);
  const positions = [["nw", x0, y0], ["n", (x0 + x1) / 2, y0], ["ne", x1, y0], ["w", x0, (y0 + y1) / 2], ["e", x1, (y0 + y1) / 2], ["sw", x0, y1], ["s", (x0 + x1) / 2, y1], ["se", x1, y1]];
  return positions.find(([, x, y]) => Math.abs(point.x - x) <= tolerance && Math.abs(point.y - y) <= tolerance)?.[0] || null;
}
async function contentShowPage() {
  const generation = contentGeneration;
  const page = contentIndex + 1;
  const file = contentActiveFile;
  contentWorking = true;
  contentControls();
  contentMessage("Loading preview...", "working");
  try {
    const response = await contentRequest("render", {page, image_format: "png", dpi: 144}, file);
    if (generation !== contentGeneration || page !== contentIndex + 1) return;
    const blob = await response.blob();
    if (generation !== contentGeneration || page !== contentIndex + 1) return;
    const url = URL.createObjectURL(blob);
    const image = new Image();
    try {
      await new Promise((resolve, reject) => {
        image.onload = resolve;
        image.onerror = () => reject(new Error("Unable to display page preview."));
        image.src = url;
      });
    } finally {
      URL.revokeObjectURL(url);
    }
    if (generation !== contentGeneration || page !== contentIndex + 1) return;
    contentImage = image;
    contentDraw();
    contentMessage("Select an editing mode to continue.", "success");
  } catch (error) {
    if (generation === contentGeneration && page === contentIndex + 1) contentMessage(error.message, "error");
  } finally {
    if (generation === contentGeneration && page === contentIndex + 1) {
      contentWorking = false;
      contentControls();
    }
  }
}
document.querySelector("#content-load").addEventListener("click", async () => {
  if (!contentFile.files.length) return;
  if (contentIsDirty() && !window.confirm(contentT("content.discard", {}, "Discard unsaved content edits?"))) return;
  const file = contentFile.files[0];
  contentReset();
  const generation = contentGeneration;
  contentActiveFile = file;
  contentWorking = true;
  contentControls();
  contentMessage("Loading PDF...", "working");
  try {
    const response = await contentRequest("info", {}, file);
    if (generation !== contentGeneration) return;
    const info = await response.json();
    if (generation !== contentGeneration) return;
    if (!Array.isArray(info.pages) || !info.pages.length) throw new Error("PDF contains no editable pages.");
    contentPages = info.pages;
    await contentShowPage();
  } catch (error) {
    if (generation === contentGeneration) {
      contentReset();
      contentMessage(error.message, "error");
    }
  } finally {
    if (generation === contentGeneration) {
      contentWorking = false;
      contentControls();
    }
  }
});
contentFile.addEventListener("change", () => {
  if (contentIsDirty() && !window.confirm(contentT("content.discard", {}, "Discard unsaved content edits?"))) {
    try {
      if (!contentActiveFile || typeof DataTransfer !== "function") throw new Error("File selection unavailable");
      const previous = new DataTransfer();
      previous.items.add(contentActiveFile);
      contentFile.files = previous.files;
    } catch { contentFile.value = ""; }
    contentMessage("Current edits were kept. Save or choose another PDF again.");
    contentControls();
    return;
  }
  contentReset();
});
for (const [selector, delta] of [["#content-prev", -1], ["#content-next", 1]]) {
  document.querySelector(selector).addEventListener("click", () => {
    if (contentWorking || contentIndex + delta < 0 || contentIndex + delta >= contentPages.length) return;
    contentCancelDrag();
    contentIndex += delta;
    contentSelected = -1;
    contentGeneration++;
    contentImage = null;
    contentShowPage();
  });
}
for (const mode of ["text", "select", "image", "replace"]) {
  document.querySelector(`#content-mode-${mode}`).addEventListener("click", () => {
    if (contentWorking) return;
    contentCancelDrag();
    contentMode = mode;
    contentDraw();
    contentControls();
  });
}
function contentPoint(event) {
  const rect = contentCanvas.getBoundingClientRect();
  return {x: Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)), y: Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height))};
}
function contentTextFields(allowEmpty = false) {
  const text = contentText.value;
  const size = Number(contentSize.value);
  if ((!allowEmpty && !text.trim()) || text.length > 250 || /[\x00-\x09\x0b-\x1f\x7f]/.test(text)) throw new Error("Enter up to 250 characters with optional line breaks.");
  if (!Number.isFinite(size) || size < 6 || size > 72) throw new Error("Font size must be between 6 and 72.");
  if (contentFontId.value === "upload" && !contentFont.files.length) throw new Error("Choose a TTF or OTF font under 10 MB.");
  if (/[^\x20-\x7e\n]/.test(text) && (contentBold.checked || contentItalic.checked)) throw new Error("Selected Unicode font does not support Bold or Italic");
  const leading = Number(contentLeading.value);
  if (!Number.isFinite(leading) || leading < 1 || leading > 2) throw new Error("Line spacing must be between 1 and 2.");
  return {text, size, color: contentColor.value, align: contentAlign.value, valign: contentVAlign.value, leading, bold: contentBold.checked, italic: contentItalic.checked};
}
function contentAutoFit(edit) {
  if (edit.type !== "text") return;
  const page = contentPages[edit.page - 1];
  if (!page) return;
  const x = Math.max(0, Math.min(edit.manualSize ? 1 : Math.max(0, 1 - edit.size * 2.5 / page.width), edit.x));
  if (!edit.manualSize) edit.x = x;
  const font = `${edit.italic ? "italic " : ""}${edit.bold ? "bold " : ""}${edit.size}px ${contentPreviewFont && !edit.bold && !edit.italic ? "ContentEditorFont" : "Arial, sans-serif"}`;
  contentContext.save();
  contentContext.font = font;
  const measured = Math.max(...edit.text.split("\n").map(line => contentContext.measureText(line).width));
  const available = Math.max(0.001, (1 - x) * page.width);
  const desired = Math.max(edit.size * 2.5, measured * 1.2 + edit.size * 1.5);
  const width = edit.manualSize ? edit.w * page.width : Math.min(available, desired);
  const safeWidth = Math.max(1, width - edit.size * 0.5);
  const lines = contentWrapText(edit.text, safeWidth);
  contentContext.restore();
  const requiredHeight = Math.max(edit.size * 1.8, (lines.length + 0.5) * edit.size * (edit.leading || 1.2) + edit.size * 0.5);
  edit.w = Math.min(1 - x, width / page.width);
  edit.h = Math.min(1, Math.max(edit.manualSize ? edit.h : 0, requiredHeight / page.height));
  edit.y = Math.max(edit.h, Math.min(1, edit.y));
}
function contentHit(point) {
  for (let i = contentEdits.length - 1; i >= 0; i--) {
    const edit = contentEdits[i];
    if (edit.page !== contentIndex + 1) continue;
    const w = edit.w || Math.max(0.02, edit.text.length * edit.size * 0.55 / contentPages[contentIndex].width);
    const h = edit.h || edit.size * 1.3 / contentPages[contentIndex].height;
    const top = edit.type === "text" ? edit.y - h : edit.y;
    if (point.x >= edit.x && point.x <= edit.x + w && point.y >= top && point.y <= top + h) return i;
  }
  return -1;
}
const contentResizeCursors = {nw: "nwse-resize", se: "nwse-resize", ne: "nesw-resize", sw: "nesw-resize", n: "ns-resize", s: "ns-resize", e: "ew-resize", w: "ew-resize"};
function contentCursor(point) {
  if (contentWorking || !contentImage) return "default";
  if (contentMode !== "select") return "crosshair";
  const selected = contentEdits[contentSelected];
  if (selected?.page === contentIndex + 1) {
    const handle = contentTextHandle(point, selected);
    if (handle) return contentResizeCursors[handle];
  }
  const index = contentHit(point);
  if (index < 0) return "default";
  const edit = contentEdits[index];
  if (edit.type === "image" && edit.w && edit.h && Math.abs(point.x - edit.x - edit.w) < 0.025 && Math.abs(point.y - edit.y - edit.h) < 0.025) return "nwse-resize";
  return "move";
}
function contentUpdateCursor(point) {
  const cursor = contentDrag ? contentDrag.mode === "text-resize" ? contentResizeCursors[contentDrag.handle] : contentDrag.mode === "resize" ? "nwse-resize" : contentDrag.mode === "move" ? "move" : "crosshair" : contentCursor(point);
  contentCanvas.dataset.cursor = cursor;
}
contentCanvas.addEventListener("pointerdown", event => {
  if (contentWorking || !contentImage) return;
  const point = contentPoint(event);
  if (contentMode === "select") {
    const current = contentEdits[contentSelected];
    const selectedHandle = current?.page === contentIndex + 1 ? contentTextHandle(point, current) : null;
    contentSelected = selectedHandle ? contentSelected : contentHit(point);
    if (contentSelected >= 0) {
      const edit = contentEdits[contentSelected];
      const handle = selectedHandle || contentTextHandle(point, edit);
      const nearCorner = edit.type === "image" && edit.w && edit.h && Math.abs(point.x - edit.x - edit.w) < 0.025 && Math.abs(point.y - edit.y - edit.h) < 0.025;
      contentDrag = {mode: handle ? "text-resize" : nearCorner ? "resize" : "move", handle, start: point, original: {x: edit.x, y: edit.y, w: edit.w, h: edit.h}, changed: false, before: JSON.stringify(contentEdits), future: contentFuture.slice()};
      if (edit.text !== undefined) {
        contentText.value = edit.text;
        contentSize.value = edit.size;
        contentColor.value = edit.color;
        contentAlign.value = edit.align || "center";
        contentVAlign.value = edit.valign || "middle";
        contentLeading.value = edit.leading || 1.2;
        contentBold.checked = !!edit.bold;
        contentItalic.checked = !!edit.italic;
      }
    }
  } else if (contentMode === "replace") {
    contentDrag = {mode: "replace", start: point, current: point};
  }
  if (contentDrag) contentCanvas.setPointerCapture(event.pointerId);
  contentUpdateCursor(point);
  contentDraw();
  contentControls();
});
contentCanvas.addEventListener("pointermove", event => {
  if (!contentImage) return;
  const point = contentPoint(event);
  contentUpdateCursor(point);
  if (!contentDrag) return;
  if (["move", "resize", "text-resize"].includes(contentDrag.mode)) {
    const edit = contentEdits[contentSelected];
    if (!edit) return;
    if (contentDrag.mode === "text-resize") {
      const original = contentDrag.original;
      const left = original.x;
      const right = original.x + original.w;
      const top = original.y - original.h;
      const bottom = original.y;
      const dx = point.x - contentDrag.start.x;
      const dy = point.y - contentDrag.start.y;
      const minW = Math.max(0.02, edit.size * 1.5 / contentPages[contentIndex].width);
      const minH = Math.max(0.02, edit.size * 1.4 / contentPages[contentIndex].height);
      const x0 = contentDrag.handle.includes("w") ? Math.max(0, Math.min(right - minW, left + dx)) : left;
      const x1 = contentDrag.handle.includes("e") ? Math.min(1, Math.max(left + minW, right + dx)) : right;
      const y0 = contentDrag.handle.includes("n") ? Math.max(0, Math.min(bottom - minH, top + dy)) : top;
      const y1 = contentDrag.handle.includes("s") ? Math.min(1, Math.max(top + minH, bottom + dy)) : bottom;
      if (!contentDrag.changed && (x0 !== edit.x || x1 - x0 !== edit.w || y1 !== edit.y || y1 - y0 !== edit.h)) { contentSnapshot(); contentDrag.changed = true; }
      edit.x = x0;
      edit.y = y1;
      edit.w = x1 - x0;
      edit.h = y1 - y0;
      edit.manualSize = true;
    } else if (contentDrag.mode === "resize") {
      const w = Math.max(0.02, Math.min(1 - edit.x, contentDrag.original.w + point.x - contentDrag.start.x));
      const h = Math.max(0.02, Math.min(1 - edit.y, contentDrag.original.h + point.y - contentDrag.start.y));
      if (edit.type === "image" && contentImageLock.checked) {
        const ratio = contentDrag.original.h / contentDrag.original.w;
        const deltaW = point.x - contentDrag.start.x;
        const deltaH = (point.y - contentDrag.start.y) / ratio;
        const target = contentDrag.original.w + (Math.abs(deltaW) >= Math.abs(deltaH) ? deltaW : deltaH);
        const nextW = Math.min(Math.max(0.02, target), 1 - edit.x, (1 - edit.y) / ratio);
        const nextH = nextW * ratio;
        if (!contentDrag.changed && (nextW !== edit.w || nextH !== edit.h)) { contentSnapshot(); contentDrag.changed = true; }
        edit.w = nextW;
        edit.h = nextH;
      } else {
        if (!contentDrag.changed && (w !== edit.w || h !== edit.h)) { contentSnapshot(); contentDrag.changed = true; }
        edit.w = w;
        edit.h = h;
      }
    } else {
      const x = Math.max(0, Math.min(1 - (edit.w || 0), contentDrag.original.x + point.x - contentDrag.start.x));
      const y = edit.type === "text" ? Math.max(edit.h || 0, Math.min(1, contentDrag.original.y + point.y - contentDrag.start.y)) : Math.max(0, Math.min(1 - (edit.h || 0), contentDrag.original.y + point.y - contentDrag.start.y));
      if (!contentDrag.changed && (x !== edit.x || y !== edit.y)) { contentSnapshot(); contentDrag.changed = true; }
      edit.x = x;
      edit.y = y;
    }
  } else contentDrag.current = point;
  contentDraw();
  if (contentDrag.mode === "replace") {
    const a = contentDrag.start;
    contentContext.strokeStyle = "#d04b4b";
    contentContext.strokeRect(Math.min(a.x, point.x) * contentCanvas.width, Math.min(a.y, point.y) * contentCanvas.height, Math.abs(point.x - a.x) * contentCanvas.width, Math.abs(point.y - a.y) * contentCanvas.height);
  }
});
contentCanvas.addEventListener("pointerup", event => {
  if (contentDrag?.mode === "replace") {
    const a = contentDrag.start;
    const b = contentPoint(event);
    const w = Math.abs(a.x - b.x);
    const h = Math.abs(a.y - b.y);
    if (w > 0.005 && h > 0.005 && contentEdits.length < 200 && window.confirm(contentT("content.redactConfirm", {}, "Permanently remove original PDF content inside this region in the exported copy?"))) {
      try {
        const fields = contentTextFields(true);
        contentSnapshot();
        contentEdits.push({id: contentNewId(), type: "replace", page: contentIndex + 1, x: Math.min(a.x, b.x), y: Math.min(a.y, b.y), w, h, ...fields});
        contentSelected = contentEdits.length - 1;
      } catch (error) { contentMessage(error.message, "error"); }
    }
  }
  contentDrag = null;
  contentUpdateCursor(contentPoint(event));
  contentDraw();
  contentControls();
});
contentCanvas.addEventListener("pointercancel", () => {
  contentCancelDrag();
  contentDraw();
  contentControls();
});
document.addEventListener("keydown", event => {
  if (contentTextDialog?.open || document.activeElement?.matches?.("input, textarea, select, button, [contenteditable]")) return;
  if (document.querySelector("#content-editor").hidden || contentWorking) return;
  const key = event.key.toLowerCase();
  if (key === "escape") {
    if (contentSelected < 0 && !contentDrag) return;
    contentCancelDrag();
    contentSelected = -1;
    contentDraw();
    contentControls();
    event.preventDefault();
  } else if ((event.ctrlKey || event.metaKey) && key === "z") {
    if (event.shiftKey ? !contentFuture.length : !contentHistory.length) return;
    document.querySelector(event.shiftKey ? "#content-redo" : "#content-undo").click();
    event.preventDefault();
  } else if ((event.ctrlKey || event.metaKey) && key === "y") {
    if (!contentFuture.length) return;
    document.querySelector("#content-redo").click();
    event.preventDefault();
  } else if (!event.ctrlKey && !event.metaKey && (key === "delete" || key === "backspace")) {
    if (contentSelected < 0) return;
    document.querySelector("#content-delete").click();
    event.preventDefault();
  } else if (!event.ctrlKey && !event.metaKey && ["arrowleft", "arrowright", "arrowup", "arrowdown"].includes(key) && contentSelected >= 0) {
    const edit = contentEdits[contentSelected];
    const page = contentPages[edit.page - 1];
    const step = event.shiftKey ? 10 : 1;
    const dx = key === "arrowleft" ? -step / page.width : key === "arrowright" ? step / page.width : 0;
    const dy = key === "arrowup" ? -step / page.height : key === "arrowdown" ? step / page.height : 0;
    const x = Math.max(0, Math.min(1 - (edit.w || 0), edit.x + dx));
    const y = edit.type === "text" ? Math.max(edit.h || 0, Math.min(1, edit.y + dy)) : Math.max(0, Math.min(1 - (edit.h || 0), edit.y + dy));
    if (x !== edit.x || y !== edit.y) {
      contentSnapshot();
      edit.x = x;
      edit.y = y;
      contentDraw();
      contentControls();
    }
    event.preventDefault();
  }
});
contentCanvas.addEventListener("dblclick", async event => {
  if (contentMode !== "select" || contentWorking) return;
  const index = contentHit(contentPoint(event));
  if (index < 0 || contentEdits[index].type !== "text") return;
  contentSelected = index;
  const edit = contentEdits[index];
  const generation = contentGeneration;
  const next = await contentAskText(edit.text, "Edit selected text");
  if (generation !== contentGeneration || contentSelected !== index || contentEdits[index] !== edit) return;
  if (next === null || next === edit.text) return;
  contentText.value = next;
  try {
    const fields = contentTextFields(edit.type === "replace");
    if (!fields.text) throw new Error("Enter text to add.");
    contentSnapshot();
    Object.assign(edit, fields);
    if (edit.type === "text") contentAutoFit(edit);
    contentDraw();
    contentControls();
    contentMessage("Selected text updated.", "success");
  } catch (error) { contentMessage(error.message, "error"); }
});
document.querySelector("#content-image-rotate").addEventListener("click", () => {
  const edit = contentEdits[contentSelected];
  if (!edit || edit.type !== "image" || contentWorking) return;
  contentSnapshot();
  edit.rotation = ((edit.rotation || 0) + 90) % 360;
  contentDraw();
  contentControls();
});
contentCanvas.addEventListener("pointerleave", () => {
  if (!contentDrag) contentCanvas.dataset.cursor = "default";
});
contentCanvas.addEventListener("click", async event => {
  if (contentWorking || !contentImage || !["text", "image"].includes(contentMode)) return;
  if (contentEdits.length >= 200) return contentMessage("Maximum 200 edits.", "error");
  const point = contentPoint(event);
  const generation = contentGeneration;
  const pageIndex = contentIndex;
  try {
    if (contentMode === "text") {
      const next = await contentAskText(contentText.value, "Add text");
      if (next === null || generation !== contentGeneration || pageIndex !== contentIndex || contentWorking || !contentImage || contentMode !== "text") return;
      contentText.value = next;
      const fields = contentTextFields();
      if (!fields.text) throw new Error("Enter text to add.");
      contentSnapshot();
      const edit = {id: contentNewId(), type: "text", page: contentIndex + 1, x: point.x, y: Math.min(1, point.y + Math.min(0.12, 1 - point.y)), w: Math.min(0.32, 1 - point.x), h: Math.min(0.12, 1 - point.y), ...fields};
      contentAutoFit(edit);
      contentEdits.push(edit);
    } else {
      const file = contentImageFile.files[0];
      if (!file || !["image/png", "image/jpeg"].includes(file.type) || file.size > 10_000_000) throw new Error("Choose a PNG or JPEG image under 10 MB.");
      if (contentImages.length >= 20) throw new Error("Maximum 20 image uploads.");
      const image = new Image();
      const url = URL.createObjectURL(file);
      try {
        await new Promise((resolve, reject) => { image.onload = resolve; image.onerror = reject; image.src = url; });
      } finally { URL.revokeObjectURL(url); }
      if (generation !== contentGeneration || pageIndex !== contentIndex || contentWorking || contentMode !== "image") return;
      const w = Math.min(0.3, 1 - point.x);
      const h = Math.min(w * image.naturalHeight / image.naturalWidth * contentPages[contentIndex].width / contentPages[contentIndex].height, 1 - point.y);
      if (w <= 0 || h <= 0) throw new Error("Choose a position inside the page.");
      contentSnapshot();
      contentImages.push({file, preview: image});
      contentEdits.push({id: contentNewId(), type: "image", page: contentIndex + 1, ...point, w, h, image: contentImages.length - 1});
    }
    contentSelected = contentEdits.length - 1;
    contentDraw();
    contentControls();
    contentMessage("Edit added. Save to export.", "success");
  } catch (error) { contentMessage(error.message || "Unable to add content.", "error"); }
});
document.querySelector("#content-apply").addEventListener("click", () => {
  if (contentWorking) return;
  const edit = contentEdits[contentSelected];
  if (!edit || edit.type === "image") return;
  try {
    const fields = contentTextFields(edit.type === "replace");
    if (edit.type === "text" && !fields.text) throw new Error("Enter text to add.");
    contentSnapshot();
    Object.assign(edit, fields);
    if (edit.type === "text") contentAutoFit(edit);
    contentDraw();
    contentControls();
    contentMessage("Selected text updated.", "success");
  } catch (error) { contentMessage(error.message, "error"); }
});
document.querySelector("#content-delete").addEventListener("click", () => {
  if (contentSelected < 0 || contentWorking) return;
  contentSnapshot();
  contentEdits.splice(contentSelected, 1);
  contentSelected = -1;
  contentDraw();
  contentControls();
});
document.querySelector("#content-undo").addEventListener("click", () => {
  if (!contentHistory.length || contentWorking) return;
  contentFuture.push(JSON.stringify(contentEdits));
  contentEdits = JSON.parse(contentHistory.pop());
  contentSelected = -1;
  contentDraw();
  contentControls();
});
document.querySelector("#content-redo").addEventListener("click", () => {
  if (!contentFuture.length || contentWorking) return;
  contentHistory.push(JSON.stringify(contentEdits));
  contentEdits = JSON.parse(contentFuture.pop());
  contentSelected = -1;
  contentDraw();
  contentControls();
});
function contentValidateSave() {
  if (!contentActiveFile) throw new Error("Load a PDF before saving.");
  if (!contentEdits.length) throw new Error("Add an edit before saving.");
  if (contentEdits.length > 200) throw new Error("Maximum 200 edits.");
  if (contentFontId.value === "upload" && (!contentFont.files.length || !/\.(ttf|otf)$/i.test(contentFont.files[0].name) || contentFont.files[0].size > 10_000_000)) throw new Error("Choose a TTF or OTF font under 10 MB.");
  for (const edit of contentEdits) {
    const page = contentPages[edit.page - 1];
    if (!page || !["text", "image", "replace"].includes(edit.type)) throw new Error("Invalid edit page or type.");
    if (![edit.x, edit.y].every(value => Number.isFinite(value) && value >= 0 && value <= 1)) throw new Error("An edit is outside the page.");
    if (edit.type === "image" || edit.type === "replace") {
      if (![edit.w, edit.h].every(value => Number.isFinite(value) && value > 0) || edit.x + edit.w > 1.000001 || edit.y + edit.h > 1.000001) throw new Error("An edit rectangle is outside the page.");
    }
    if (edit.type === "image") {
      const asset = contentImages[edit.image];
      if (!asset?.file || !["image/png", "image/jpeg"].includes(asset.file.type) || asset.file.size <= 0 || asset.file.size > 10_000_000 || ![0, 90, 180, 270].includes(edit.rotation || 0)) throw new Error("Choose a valid PNG or JPEG image before saving.");
      continue;
    }
    if (edit.type === "replace" && !edit.text) continue;
    if (typeof edit.text !== "string" || !edit.text.trim() || edit.text.length > 250 || /[\x00-\x09\x0b-\x1f\x7f]/.test(edit.text)) throw new Error("An edit contains invalid text.");
    if (!Number.isFinite(edit.size) || edit.size < 6 || edit.size > 72 || !/^#[0-9a-f]{6}$/i.test(edit.color)) throw new Error("An edit has invalid text formatting.");
    if (!["left", "center", "right"].includes(edit.align || "center") || !["top", "middle", "bottom"].includes(edit.valign || "middle") || !Number.isFinite(edit.leading ?? 1.2) || (edit.leading ?? 1.2) < 1 || (edit.leading ?? 1.2) > 2) throw new Error("An edit has invalid text alignment or spacing.");
    if (/[^\x20-\x7e\n]/.test(edit.text) && (edit.bold || edit.italic)) throw new Error("Selected Unicode font does not support Bold or Italic");
    if (edit.type === "text" && (edit.w !== undefined || edit.h !== undefined)) {
      if (![edit.w, edit.h].every(value => Number.isFinite(value) && value > 0) || edit.x + edit.w > 1.000001 || edit.y - edit.h < -0.000001) throw new Error("A text box is outside the page.");
      if (edit.h * page.height < edit.size * 0.9) throw new Error("A text box is too short. Enlarge it or reduce the font size.");
      contentContext.save();
      contentContext.font = `${edit.italic ? "italic " : ""}${edit.bold ? "bold " : ""}${edit.size}px ${contentPreviewFont && !edit.bold && !edit.italic ? "ContentEditorFont" : "Arial, sans-serif"}`;
      const lines = contentWrapText(edit.text, edit.w * page.width - 1);
      contentContext.restore();
      if (lines.length * edit.size * (edit.leading || 1.2) * 0.75 > edit.h * page.height) throw new Error("Text may not fit in its box. Enlarge it or reduce the font size.");
    }
  }
}
document.querySelector("#content-save").addEventListener("click", async () => {
  if (contentWorking) return;
  contentCancelDrag();
  try { contentValidateSave(); } catch (error) { contentMessage(error.message, "error"); return; }
  const generation = contentGeneration;
  const savedSnapshot = JSON.stringify(contentEdits);
  contentWorking = true;
  contentControls();
  contentMessage("Saving content...", "working");
  try {
    const response = await contentRequest("content-edit", {edits: JSON.stringify(contentEdits.map(({id, manualSize, ...edit}) => edit)), font_id: contentFontId.value}, contentFile.files[0], true);
    if (generation !== contentGeneration) return;
    const blob = await response.blob();
    if (generation !== contentGeneration) return;
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "content-edited.pdf";
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
    if (JSON.stringify(contentEdits) === savedSnapshot) {
      contentSavedState = savedSnapshot;
      contentMessage("Content PDF saved successfully.", "success");
    } else contentMessage("PDF saved. Newer edits are still unsaved.", "info");
  } catch (error) {
    if (generation === contentGeneration) contentMessage(error.message, "error");
  } finally {
    if (generation === contentGeneration) {
      contentWorking = false;
      contentControls();
    }
  }
});
window.addEventListener("beforeunload", event => {
  if (!contentIsDirty()) return;
  event.preventDefault();
  event.returnValue = "";
});
window.addEventListener("pagehide", contentReset);
document.addEventListener("pdf-toolkit-language-change", () => { contentControls(); contentDraw(); });
contentControls();
