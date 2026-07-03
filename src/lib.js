const fs = require("fs");
const path = require("path");

const ROOT = path.join(__dirname, "..");
const CONTENT = path.join(ROOT, "content");
const TEMPLATES = path.join(ROOT, "templates");
const PENDING = path.join(ROOT, "out", "pending");
const PUBLISHED = path.join(ROOT, "out", "published");

function loadJSON(p) {
  return JSON.parse(fs.readFileSync(p, "utf8"));
}
function saveJSON(p, obj) {
  fs.writeFileSync(p, JSON.stringify(obj, null, 2) + "\n");
}

const themes = () => loadJSON(path.join(CONTENT, "themes.json"));
const statePath = path.join(CONTENT, "state.json");
const state = () => loadJSON(statePath);
const saveState = (s) => saveJSON(statePath, s);

function fontB64(pkgFile) {
  const p = path.join(ROOT, "node_modules", pkgFile);
  return fs.readFileSync(p).toString("base64");
}

/** Fill {{placeholders}} in a template string. Unmatched keys become empty. */
function fill(tpl, data) {
  return tpl.replace(/\{\{(\w+)\}\}/g, (_, key) =>
    data[key] !== undefined ? String(data[key]) : ""
  );
}

/** Build the final HTML for a card template with fonts + base injected. */
function buildHTML(templateName, data) {
  const base = fs.readFileSync(path.join(TEMPLATES, "_base.html"), "utf8");
  const tpl = fs.readFileSync(path.join(TEMPLATES, `${templateName}.html`), "utf8");

  const baseFilled = fill(base, {
    font_display: fontB64("@fontsource/archivo-black/files/archivo-black-latin-400-normal.woff2"),
    font_body: fontB64("@fontsource/inter/files/inter-latin-400-normal.woff2"),
    font_body_semibold: fontB64("@fontsource/inter/files/inter-latin-600-normal.woff2"),
    font_mono: fontB64("@fontsource/jetbrains-mono/files/jetbrains-mono-latin-500-normal.woff2"),
  });

  return fill(tpl, { ...data, __base: baseFilled });
}

module.exports = {
  ROOT, PENDING, PUBLISHED,
  themes, state, saveState, loadJSON, saveJSON, buildHTML,
};
