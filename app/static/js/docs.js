document.addEventListener("DOMContentLoaded", async () => {
  const status = document.querySelector("#docs-status");
  const list = document.querySelector("#docs-list");
  try {
    const response = await fetch("/openapi.json", {credentials: "same-origin"});
    if (!response.ok) throw new Error("Unable to load the API schema.");
    const schema = await response.json();
    let count = 0;
    for (const [path, methods] of Object.entries(schema.paths || {}).sort(([a], [b]) => a.localeCompare(b))) {
      for (const [method, operation] of Object.entries(methods)) {
        if (!operation || typeof operation !== "object" || !operation.responses) continue;
        const section = document.createElement("section");
        section.className = "endpoint";
        const heading = document.createElement("h2");
        heading.textContent = `${method.toUpperCase()} ${path}`;
        const summary = document.createElement("p");
        summary.textContent = operation.summary || operation.description || "PDF operation";
        const details = document.createElement("details");
        const label = document.createElement("summary");
        label.textContent = "Request and response schema";
        const pre = document.createElement("pre");
        pre.textContent = JSON.stringify({parameters: operation.parameters || [], requestBody: operation.requestBody || null, responses: operation.responses}, null, 2);
        details.append(label, pre);
        section.append(heading, summary, details);
        list.append(section);
        count++;
      }
    }
    status.textContent = `${count} API operations available.`;
  } catch {
    status.textContent = "Unable to load the API schema. Open the JSON link or try again.";
  }
});
