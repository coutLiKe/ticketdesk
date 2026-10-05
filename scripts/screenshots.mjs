// Regenerates the README screenshots from the running app (docker compose up + seed first).
// Drives headless Chrome over its DevTools protocol, so it needs no extra npm packages.
//   node scripts/screenshots.mjs
import { spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CHROME = process.env.CHROME ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const BASE = process.env.BASE_URL ?? "http://localhost:5173";
const OUT = "docs/screenshots";
const PORT = 9333;
const PASSWORD = "demo1234";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const chrome = spawn(CHROME, [
  "--headless=new", `--remote-debugging-port=${PORT}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), "td-"))}`,
  "--hide-scrollbars", "--no-first-run", "about:blank",
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
const evaluate = (expression) => send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });

async function login(email) {
  await send("Page.navigate", { url: `${BASE}/login` });
  await sleep(1200);
  await evaluate(`(async () => {
    localStorage.clear();
    const r = await fetch("/api/auth/login", {method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({email: ${JSON.stringify(email)}, password: ${JSON.stringify(PASSWORD)}})});
    localStorage.setItem("ticketdesk_token", (await r.json()).access_token);
  })()`);
}

async function shot(name, path, height = 800) {
  await send("Emulation.setDeviceMetricsOverride", { width: 1280, height, deviceScaleFactor: 1, mobile: false });
  await send("Page.navigate", { url: `${BASE}${path}` });
  await sleep(2000);
  const { data } = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(`${OUT}/${name}.png`, Buffer.from(data, "base64"));
  console.log("saved", `${OUT}/${name}.png`);
}

mkdirSync(OUT, { recursive: true });
await send("Page.enable");
await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "light" }] });

await shot("login", "/login", 700);
await login("tom@ticketdesk.dev");
await shot("tickets-staff", "/tickets", 760);
await shot("ticket-detail-staff", "/tickets/1", 900);
await shot("assets", "/assets", 700);
await shot("asset-detail", "/assets/1", 600);
await login("rita@ticketdesk.dev");
await shot("ticket-detail-requester", "/tickets/1", 760);
await login("admin@ticketdesk.dev");
await shot("users-admin", "/users", 560);

ws.close();
chrome.kill();
