// Generates the PNG favicons from frontend/public/favicon.svg using headless Chrome.
//   node scripts/icons.mjs
// favicon-32.png        32x32, transparent corners (browser tab fallback)
// apple-touch-icon.png  180x180, full-bleed square (iOS rounds the corners itself)
import { spawn } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CHROME = process.env.CHROME ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const PORT = 9334;
const OUT = "frontend/public";
const svg = readFileSync(`${OUT}/favicon.svg`, "utf8");
const squareSvg = svg.replace(/ rx="14"/, ""); // drop the rounded corners

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const chrome = spawn(CHROME, [
  "--headless=new", `--remote-debugging-port=${PORT}`,
  `--user-data-dir=${mkdtempSync(join(tmpdir(), "td-icons-"))}`, "--no-first-run", "about:blank",
], { stdio: "ignore" });

async function connect() {
  for (let i = 0; i < 50; i++) {
    try {
      const pages = await (await fetch(`http://localhost:${PORT}/json/list`)).json();
      const page = pages.find((p) => p.type === "page");
      if (page) return page.webSocketDebuggerUrl;
    } catch { /* Chrome still starting */ }
    await sleep(200);
  }
  throw new Error("Could not connect to Chrome");
}

const ws = new WebSocket(await connect());
await new Promise((r) => (ws.onopen = r));
let nextId = 0;
const pending = new Map();
ws.onmessage = (m) => {
  const msg = JSON.parse(m.data);
  if (msg.id && pending.has(msg.id)) pending.get(msg.id)(msg);
};
const send = (method, params = {}) =>
  new Promise((resolve, reject) => {
    const id = ++nextId;
    pending.set(id, (msg) => (msg.error ? reject(new Error(msg.error.message)) : resolve(msg.result)));
    ws.send(JSON.stringify({ id, method, params }));
  });

async function render(source, size, file) {
  const html = `<body style="margin:0;background:transparent">${source.replace("<svg ", `<svg width="${size}" height="${size}" style="display:block" `)}</body>`;
  await send("Emulation.setDeviceMetricsOverride", { width: size, height: size, deviceScaleFactor: 1, mobile: false });
  await send("Emulation.setDefaultBackgroundColorOverride", { color: { r: 0, g: 0, b: 0, a: 0 } });
  await send("Page.navigate", { url: `data:text/html;charset=utf-8,${encodeURIComponent(html)}` });
  await sleep(500);
  const { data } = await send("Page.captureScreenshot", { format: "png", clip: { x: 0, y: 0, width: size, height: size, scale: 1 } });
  writeFileSync(`${OUT}/${file}`, Buffer.from(data, "base64"));
  console.log("saved", `${OUT}/${file}`);
}

await send("Page.enable");
await render(svg, 32, "favicon-32.png");
await render(squareSvg, 180, "apple-touch-icon.png");
ws.close();
chrome.kill();
