(function () {
  const selectors = ["#content-font-id", "#unicode-font-id"];
  let fonts = [];
  const t = (key, fallback) => window.pdfToolkitI18n?.t(key, {}, fallback) || fallback;
  function render() {
    for (const selector of selectors) {
      const select = document.querySelector(selector);
      if (!select) continue;
      const previous = select.value;
      select.replaceChildren();
      for (const font of fonts) {
        const option = document.createElement("option");
        option.value = font.id;
        option.textContent = font.id === "default" ? `${t("fonts.default", "Default font")} — ${font.name}` : font.name;
        select.append(option);
      }
      const upload = document.createElement("option");
      upload.value = "upload";
      upload.textContent = t("fonts.upload", "Upload custom font (TTF/OTF)");
      select.append(upload);
      select.value = [...select.options].some(option => option.value === previous) ? previous : fonts.some(font => font.id === "default") ? "default" : "upload";
      select.dispatchEvent(new Event("change"));
    }
  }
  window.pdfToolkitFonts = {get: id => fonts.find(font => font.id === id)};
  document.addEventListener("pdf-toolkit-language-change", render);
  document.addEventListener("DOMContentLoaded", async () => {
    try {
      const response = await fetch("/api/pdf/fonts");
      if (!response.ok) throw new Error("Font list unavailable");
      const payload = await response.json();
      fonts = Array.isArray(payload.fonts) ? payload.fonts.filter(font => ["default", "noto-serif-kr", "nanum-gothic"].includes(font.id) && typeof font.name === "string") : [];
    } catch {
      fonts = [];
    }
    render();
  });
})();
