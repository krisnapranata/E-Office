#!/usr/bin/env node
// Uji end-to-end LAPIS 2 (browser headless patchright) terhadap runserver/container dev — pola casemix.
//   KEY=$(.venv/bin/python tools/e2e/browser/sesi.py --user direktur)
//   node tools/e2e/browser/e2e.cjs --sesi $KEY [--base http://127.0.0.1:8011] [--hp] [--layar DIR] [--hanya /tugas/]
//   .venv/bin/python tools/e2e/browser/sesi.py --hapus $KEY
// Yang diuji:
//  1. Setiap menu sidebar (aside#sidebar a.sidebar-link) DIKLIK: URL berubah, link menu jadi .active,
//     #workspace terisi, tanpa console error / pageerror / respons >=500 / dialihkan ke login / CSS/JS 404.
//  2. Sidebar melebar saat di-hover, pin (#sidebarToggle) tersimpan setelah muat ulang.
//  3. --hp: setiap menu dibuka di lebar 390 px -> tanpa scroll samping, tombol menu offcanvas berfungsi.
// AMAN: semua permintaan selain GET/HEAD dari browser DIBATALKAN (runserver tidak bisa di-rollback);
// alur simpan/ubah/hapus diuji di lapis 1 (tools/e2e/jalankan.py) dan lapis 2b (test_alur.py).
const fs = require("fs"), path = require("path");
const arg = (n, b) => { const i = process.argv.indexOf(n); return i > 0 ? process.argv[i + 1] : b; };
const ada = n => process.argv.includes(n);
const pr = require("./_patchright.cjs")();
if (!pr) { console.error("patchright tidak ditemukan (set E2E_PATCHRIGHT atau pasang ekstensi CodeGPT)"); process.exit(2); }
const { chromium } = pr;
const BASE = arg("--base", "http://127.0.0.1:8011"), sesi = arg("--sesi");
const LAYAR = arg("--layar", ""), HANYA = arg("--hanya", "");
if (!sesi) { console.error("--sesi KUNCI wajib (tools/e2e/browser/sesi.py --user ...)"); process.exit(2); }
if (LAYAR) fs.mkdirSync(LAYAR, { recursive: true });

const hasil = [];
function catat(nama, ok, pesan) {
  hasil.push({ nama, ok, pesan });
  console.log(`[${ok ? "OK   " : "GAGAL"}] ${nama}${pesan ? "\n        " + pesan : ""}`);
}

(async () => {
  const b = await chromium.launch({ headless: true, channel: "chromium", args: ["--no-sandbox", "--disable-dev-shm-usage"] });
  const ctx = await b.newContext({ viewport: { width: 1440, height: 950 } });
  await ctx.addCookies([{ name: "sessionid", value: sesi, url: BASE }]);
  const dicegah = [];
  await ctx.route("**/*", r => {
    const m = r.request().method();
    if (m !== "GET" && m !== "HEAD" && r.request().url().startsWith(BASE)) {
      dicegah.push(`${m} ${r.request().url().replace(BASE, "")}`);
      return r.abort();
    }
    return r.continue();
  });
  const p = await ctx.newPage();
  let err = [], gagal = [];
  p.on("console", m => { if (m.type() === "error") err.push(m.text().slice(0, 200)); });
  p.on("pageerror", e => err.push("pageerror: " + String(e).slice(0, 200)));
  p.on("response", r => {
    if (!r.url().startsWith(BASE)) return;
    if (r.status() >= 500) gagal.push(`${r.status()} ${r.url().replace(BASE, "")}`);
    if (r.status() === 404 && /\/static\//.test(r.url())) gagal.push(`404 aset ${r.url().replace(BASE, "")}`);
  });
  const reset = () => { err = []; gagal = []; };
  const bersih = () => err.filter(e => !/net::ERR_FAILED|Failed to fetch|ERR_BLOCKED/.test(e));
  const ringkas = () => [...bersih().map(e => "console: " + e), ...gagal.map(g => "HTTP " + g)].slice(0, 5).join(" | ");

  await p.goto(BASE + "/", { waitUntil: "networkidle", timeout: 60000 });
  if (p.url().includes("/login")) { console.error("sesi tidak valid -> halaman login. Buat ulang dengan sesi.py"); process.exit(2); }
  const menu = await p.$$eval("aside#sidebar a.sidebar-link[href]", as => {
    const lihat = new Set(), out = [];
    for (const a of as) { const h = a.getAttribute("href"); if (!lihat.has(h)) { lihat.add(h); out.push({ href: h, label: (a.getAttribute("aria-label") || a.textContent).trim() }); } }
    return out;
  });
  console.log(`${menu.length} menu sidebar\n`);

  // ---------------------------------------------------------------- 1. klik setiap menu sidebar
  for (const m of menu) {
    if (HANYA && !m.href.startsWith(HANYA)) continue;
    if (m.href.startsWith("/admin/")) { catat(`Menu ${m.label} (${m.href})`, true, "dilewati: admin Django"); continue; }
    reset();
    try {
      if (new URL(p.url()).pathname === m.href) await p.goto(BASE + "/notifikasi/", { waitUntil: "networkidle" });
      reset();
      await p.hover("aside#sidebar");
      await Promise.all([p.waitForURL(u => new URL(u).pathname === m.href, { timeout: 20000 }),
                         p.click(`aside#sidebar a.sidebar-link[href="${m.href}"]`)]);
      await p.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
      const info = await p.evaluate(h => ({
        isi: ((document.getElementById("workspace") || document.body).innerText || "").trim().length,
        aktif: !!document.querySelector(`aside#sidebar a.sidebar-link.active[href="${h}"]`),
        h1: (document.querySelector("#workspace h1") || {}).textContent || "",
      }), m.href);
      const masalah = [];
      if (p.url().includes("/login")) masalah.push("dialihkan ke login");
      if (info.isi < 20) masalah.push(`#workspace kosong (${info.isi} karakter)`);
      if (!info.aktif) masalah.push("link menu tidak ditandai .active");
      if (!info.h1.trim()) masalah.push("tanpa judul h1");
      const r = ringkas(); if (r) masalah.push(r);
      if (LAYAR) await p.screenshot({ path: path.join(LAYAR, "menu" + m.href.replace(/\W+/g, "_") + ".png") });
      catat(`Menu ${m.label} (${m.href})`, !masalah.length, masalah.join(" | "));
    } catch (e) {
      catat(`Menu ${m.label} (${m.href})`, false, String(e).split("\n")[0]);
      await p.goto(BASE + "/", { waitUntil: "networkidle" }).catch(() => {});
    }
  }

  // ---------------------------------------------------------------- 2. sidebar hover & pin
  if (!HANYA) {
    try {
      await p.goto(BASE + "/", { waitUntil: "networkidle" });
      await p.mouse.move(900, 500);
      await p.waitForTimeout(400);
      const ramping = await p.$eval("aside#sidebar", e => e.getBoundingClientRect().width);
      await p.hover("aside#sidebar");
      await p.waitForTimeout(500);
      const lebar = await p.$eval("aside#sidebar", e => e.getBoundingClientRect().width);
      catat("Sidebar melebar saat hover", lebar > ramping + 100, `${Math.round(ramping)}px -> ${Math.round(lebar)}px`);
      await p.click("#sidebarToggle");
      await p.reload({ waitUntil: "networkidle" });
      const pin = await p.evaluate(() => document.body.classList.contains("sidebar-pinned"));
      await p.click("#sidebarToggle");          // kembalikan
      catat("Pin sidebar tersimpan setelah muat ulang", pin, "");
    } catch (e) { catat("Sidebar hover/pin", false, String(e).split("\n")[0]); }
  }

  // ---------------------------------------------------------------- 3. lebar HP
  if (ada("--hp")) {
    await p.setViewportSize({ width: 390, height: 900 });
    for (const m of menu) {
      if (HANYA && !m.href.startsWith(HANYA)) continue;
      if (m.href.startsWith("/admin/")) continue;
      reset();
      await p.goto(BASE + m.href, { waitUntil: "networkidle", timeout: 60000 }).catch(() => {});
      const w = await p.evaluate(() => document.documentElement.scrollWidth);
      const masalah = [];
      if (w > 392) masalah.push(`lebar dokumen ${w}px (scroll samping)`);
      const r = ringkas(); if (r) masalah.push(r);
      if (LAYAR) await p.screenshot({ path: path.join(LAYAR, "hp" + m.href.replace(/\W+/g, "_") + ".png") });
      catat(`HP 390px ${m.href}`, !masalah.length, masalah.join(" | "));
    }
    try {
      await p.goto(BASE + "/", { waitUntil: "networkidle" });
      await p.click("button.menu-toggle-topbar");
      await p.waitForSelector("#mobileSidebar.show", { timeout: 5000 });
      catat("HP: tombol menu membuka sidebar offcanvas", true, "");
    } catch (e) { catat("HP: tombol menu membuka sidebar offcanvas", false, String(e).split("\n")[0]); }
  }

  await b.close();
  const n = hasil.filter(h => !h.ok).length;
  console.log(`\n${hasil.length} pemeriksaan, ${hasil.length - n} lolos, ${n} gagal · ${dicegah.length} POST dari browser dicegah`);
  if (dicegah.length) console.log("POST dicegah (contoh):", [...new Set(dicegah)].slice(0, 6).join(", "));
  process.exit(n ? 1 : 0);
})();
