const form = document.querySelector("#tool-form");
const appT = (key, params = {}, fallback = "") => window.pdfToolkitI18n?.t(key, params, fallback) || fallback;
const appTranslate = value => window.pdfToolkitI18n?.translate(value) || value;
const operation = document.querySelector("#operation");
const unicodeFontId = document.querySelector("#unicode-font-id");
unicodeFontId.addEventListener("change", () => {
  const uploading = unicodeFontId.value === "upload";
  document.querySelector("#unicode-font-upload").hidden = !uploading;
  if (!uploading) document.querySelector("#unicode-font").value = "";
});
const files = document.querySelector("#files");
const status = document.querySelector("#status");
const dropZone = document.querySelector("#drop-zone");
const fileSummary = document.querySelector("#file-summary");
const progressTrack = document.querySelector("#progress-track");
const progressBar = document.querySelector("#progress-bar");
let selectedFiles = [];
let infoRequest = 0;
const mergeOrder = document.querySelector("#merge-order");
const mergeList = document.querySelector("#merge-list");
const downloadPanel = document.querySelector("#download-panel");
const downloadLink = document.querySelector("#download-link");
let downloadUrl = null;
let processing = false;
function syncFileInput() {
  const transfer = new DataTransfer();
  selectedFiles.forEach(file => transfer.items.add(file));
  files.files = transfer.files;
}
function renderMergeOrder() {
  mergeOrder.hidden = operation.value !== "merge" || selectedFiles.length === 0;
  mergeList.replaceChildren();
  selectedFiles.forEach((file, index) => {
    const item = document.createElement("li");
    const name = document.createElement("span");
    name.textContent = `${file.name} (${formatSize(file.size)})`;
    item.append(name);
    for (const [label, action, disabled] of [[appT("common.up", {}, "Up"), "up", index === 0], [appT("common.down", {}, "Down"), "down", index === selectedFiles.length - 1], [appT("common.remove", {}, "Remove"), "remove", false]]) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = label;
      button.disabled = disabled;
      button.addEventListener("click", () => {
        if (processing) return;
        if (action === "remove") selectedFiles.splice(index, 1);
        else {
          const other = action === "up" ? index - 1 : index + 1;
          [selectedFiles[index], selectedFiles[other]] = [selectedFiles[other], selectedFiles[index]];
        }
        syncFileInput();
        showFiles([...selectedFiles]);
      });
      item.append(button);
    }
    mergeList.append(item);
  });
}
function resetDownload() {
  downloadPanel.hidden = true;
  downloadLink.removeAttribute("href");
  if (downloadUrl) URL.revokeObjectURL(downloadUrl);
  downloadUrl = null;
}
function outputName(op) {
  const base = (selectedFiles[0]?.name || "document.pdf").replace(/\.pdf$/i, "").replace(/[^a-zA-Z0-9._-]/g, "_").slice(0, 70) || "document";
  if (op === "render") return `${base}-page-${document.querySelector("#page").value}.${document.querySelector("#image_format").value === "jpeg" ? "jpg" : "png"}`;
  if (op === "split") return `${base}-split.zip`;
  if (op === "text") return `${base}-text.txt`;
  if (op === "merge") return "merged.pdf";
  return `${base}-${op}.pdf`;
}
const processButton = document.querySelector("#process-button");
const requirement = document.querySelector("#file-requirement");
const documentInfo = document.querySelector("#document-info");
const optionsArea = document.querySelector("#options-area");
const splitMode = document.querySelector("#mode");
const pageLabel = document.querySelector('label[for="pages"]');
const singleFileOperations = new Set(["extract", "split", "rotate", "render", "compress", "watermark", "protect", "text", "unicode-watermark", "image-watermark"]);
function syncPageLabel() {
  if (operation.value === "split") pageLabel.textContent = splitMode.value === "ranges" ? appT("pdfTools.rangesRequired", {}, "Ranges (required; e.g. 1-3,4-6)") : appT("pdfTools.pagesAll", {}, "Pages (optional for all pages)");
  else if (operation.value === "extract") pageLabel.textContent = appT("pdfTools.pagesExtract", {}, "Pages to extract (e.g. 1,3-5)");
  else pageLabel.textContent = appT("pdfTools.pagesOptional", {}, "Pages (optional; e.g. 1,3-5)");
}
function updateAvailability() {
  const merge = operation.value === "merge";
  const valid = merge ? selectedFiles.length >= 2 : selectedFiles.length === 1;
  processButton.disabled = processing || !valid;
  requirement.textContent = merge ? appT("upload.many", {}, "Select at least two PDF files to merge.") : appT("upload.one", {}, "Select one PDF file.");
  requirement.classList.toggle("ready", valid);
}
async function loadDocumentInfo(items) {
  const request = ++infoRequest;
  documentInfo.hidden = true;
  documentInfo.replaceChildren();
  if (items.length !== 1) return;
  const data = new FormData();
  data.append("file", items[0]);
  try {
    const response = await fetch("/api/pdf/info", {method: "POST", body: data});
    if (!response.ok) return;
    const info = await response.json();
    if (request !== infoRequest) return;
    const parts = [];
    if (Number.isInteger(info.page_count)) parts.push(`${info.page_count} pages`);
    if (Number.isInteger(info.pages)) parts.push(`${info.pages} pages`);
    if (parts.length) {
      documentInfo.textContent = appT("files.documentPages", {count: info.page_count ?? info.pages}, `Document: ${parts[0]}`);
      documentInfo.hidden = false;
    }
  } catch (error) {
    if (request === infoRequest) documentInfo.hidden = true;
  }
}
const formatSize = size => size < 1048576 ? `${(size / 1024).toFixed(1)} KB` : `${(size / 1048576).toFixed(2)} MB`;
function setStatus(message, kind = "neutral") {
  status.textContent = appTranslate(message);
  document.querySelector("#status-panel").dataset.kind = kind;
}
function showFiles(items) {
  selectedFiles = items;
  resetDownload();
  renderMergeOrder();
  fileSummary.replaceChildren();
  if (!items.length) { fileSummary.textContent = appT("upload.none", {}, "No files selected"); updateAvailability(); loadDocumentInfo([]); return; }
  const list = document.createElement("ul");
  for (const file of items) {
    const item = document.createElement("li");
    item.textContent = `${file.name} · ${formatSize(file.size)}`;
    list.append(item);
  }
  fileSummary.append(list);
  updateAvailability();
  loadDocumentInfo(items);
}
function assignFiles(items) {
  const pdfs = items.filter(file => file.name.toLowerCase().endsWith(".pdf") || file.type === "application/pdf");
  if (pdfs.length !== items.length) { setStatus(appT("files.onlyPdf", {}, "Only PDF files are supported."), "error"); return; }
  const chosen = operation.value === "merge" ? pdfs : pdfs.slice(0, 1);
  selectedFiles = chosen;
  syncFileInput();
  showFiles(chosen);
  if (chosen.length !== pdfs.length) setStatus(appT("files.singleLimited", {}, "This operation accepts one PDF. The first file was selected."));
  else setStatus("");
}
files.addEventListener("change", () => assignFiles([...files.files]));
dropZone.addEventListener("dragover", event => { event.preventDefault(); dropZone.classList.add("drag-active"); });
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-active"));
dropZone.addEventListener("drop", event => { event.preventDefault(); dropZone.classList.remove("drag-active"); assignFiles([...event.dataTransfer.files]); });
dropZone.addEventListener("click", event => { if (event.target !== files) files.click(); });
dropZone.addEventListener("keydown", event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); files.click(); } });
document.querySelectorAll(".nav-button").forEach(button => button.addEventListener("click", () => {
  document.querySelectorAll(".nav-button").forEach(item => { const active = item === button; item.classList.toggle("active", active); item.setAttribute("aria-pressed", String(active)); });
  document.querySelectorAll(".workspace-panel").forEach(panel => { panel.hidden = panel.id !== button.dataset.panel; });
}));
const rows = {pages: document.querySelector("#pages-row"), angle: document.querySelector("#angle-row"), image: document.querySelector("#image-row"), split: document.querySelector("#split-row"), watermark: document.querySelector("#watermark-row"), protect: document.querySelector("#protect-row"), unicode: document.querySelector("#unicode-row"), imageWatermark: document.querySelector("#image-watermark-row")};
function update() {
  const op = operation.value;
  rows.pages.hidden = !["extract", "split", "rotate", "text"].includes(op);
  syncPageLabel();
  rows.angle.hidden = op !== "rotate";
  rows.image.hidden = op !== "render";
  rows.split.hidden = op !== "split";
  rows.watermark.hidden = op !== "watermark";
  rows.protect.hidden = op !== "protect";
  rows.unicode.hidden = op !== "unicode-watermark";
  rows.imageWatermark.hidden = op !== "image-watermark";
  optionsArea.hidden = ["merge", "compress"].includes(op);
  files.multiple = op === "merge";
  files.value = "";
  showFiles([]);
  setStatus("");
}
operation.addEventListener("change", update);
document.addEventListener("pdf-toolkit-language-change", () => {
  renderMergeOrder();
  updateAvailability();
  syncPageLabel();
  if (!selectedFiles.length) fileSummary.textContent = appT("upload.none", {}, "No files selected");
});
splitMode.addEventListener("change", () => {
  if (operation.value === "split") syncPageLabel();
});
update();
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const op = operation.value;
  const selected = [...files.files];
  if (!selected.length || (op === "merge" && selected.length < 2)) {
    setStatus("Select the required PDF files.", "error");
    return;
  }
  const data = new FormData();
  for (const file of selected) data.append(op === "merge" ? "files" : "file", file);
  if (["extract", "split", "rotate", "text"].includes(op)) {
    const pages = document.querySelector("#pages").value.trim();
    if ((op === "extract" || (op === "split" && splitMode.value === "ranges")) && !pages) { setStatus("Enter the required page ranges.", "error"); return; }
    if (pages) data.append("pages", pages);
  }
  if (op === "rotate") data.append("angle", document.querySelector("#angle").value);
  if (op === "split") data.append("mode", document.querySelector("#mode").value);
  if (op === "render") {
    for (const key of ["page", "image_format", "dpi"]) data.append(key, document.querySelector(`#${key}`).value);
  }
  if (op === "watermark") {
    const value = document.querySelector("#watermark-text").value;
    if (!value || !/^[\x20-\x7E]{1,120}$/.test(value)) { setStatus("Enter 1-120 printable ASCII characters.", "error"); return; }
    data.append("text", value);
    data.append("font_size", document.querySelector("#watermark-size").value);
    data.append("opacity", document.querySelector("#watermark-opacity").value);
    data.append("position", document.querySelector("#watermark-position").value);
  }
  if (op === "unicode-watermark") {
    const font = document.querySelector("#unicode-font").files[0];
    const text = document.querySelector("#unicode-text").value;
    if (!text.trim() || (unicodeFontId.value === "upload" && !font)) { setStatus("Select a font and enter watermark text.", "error"); return; }
    data.append("font_id", unicodeFontId.value);
    if (unicodeFontId.value === "upload") data.append("font", font);
    data.append("text", text);
    data.append("font_size", document.querySelector("#unicode-size").value);
    data.append("opacity", document.querySelector("#unicode-opacity").value);
    data.append("position", document.querySelector("#unicode-position").value);
  }
  if (op === "image-watermark") {
    const image = document.querySelector("#watermark-image").files[0];
    if (!image) { setStatus("Select a PNG or JPEG image.", "error"); return; }
    data.append("image", image);
    data.append("scale", document.querySelector("#image-scale").value);
    data.append("opacity", document.querySelector("#image-opacity").value);
    data.append("position", document.querySelector("#image-position").value);
  }
  if (op === "protect") {
    const password = document.querySelector("#protect-password").value;
    if (password.length < 8 || password.length > 128) { setStatus("Password must contain 8-128 characters.", "error"); return; }
    data.append("password", password);
  }
  processing = true;
  resetDownload();
  updateAvailability();
  setStatus("Processing... Please wait.", "working");
  progressTrack.hidden = false;
  progressBar.classList.add("indeterminate");
  try {
    const response = await fetch(`/api/pdf/${op}`, {method: "POST", body: data});
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(typeof error.detail === "string" ? error.detail : "Processing failed");
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    downloadUrl = url;
    const link = document.createElement("a");
    link.href = url;
    link.download = outputName(op);
    downloadLink.href = url;
    downloadLink.download = link.download;
    downloadPanel.hidden = false;
    link.click();

    setStatus("Completed. Your download should begin automatically.", "success");
  } catch (error) { setStatus(error.message, "error"); }
  finally { processing = false; updateAvailability(); progressTrack.hidden = true; progressBar.classList.remove("indeterminate"); }
});
