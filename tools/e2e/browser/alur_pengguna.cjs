#!/usr/bin/env node
// Lapis 2b: alur Pengguna di browser (DB test, dijalankan oleh test_alur.py).
// Admin membuka Master Organisasi -> ikon "tambah pengguna" di Kepala Seksi HRD -> jabatan/peran terisi otomatis ->
// simpan kepala -> tambah staf Diklat: atasan otomatis = kepala HRD -> daftar per bidang -> HP 390 px tanpa scroll samping.
const fs = require("fs"), path = require("path");
const arg = (n, b) => { const i = process.argv.indexOf(n); return i > 0 ? process.argv[i + 1] : b; };
const pr = require("./_patchright.cjs")();
if (!pr) { console.error("patchright tidak ditemukan"); process.exit(2); }
const BASE = arg("--base"), PFX = arg("--prefix", "e2e_"), SANDI = process.env.E2E_SANDI, LAYAR = arg("--layar", "");
if (!BASE || !SANDI) { console.error("--base dan env E2E_SANDI wajib"); process.exit(2); }
if (LAYAR) fs.mkdirSync(LAYAR, { recursive: true });
const catat = (nama, ok, pesan = "") => { console.log(`[${ok ? "OK   " : "GAGAL"}] ${nama}${pesan ? " — " + pesan : ""}`); if (!ok) throw new Error(nama + ": " + pesan); };

(async () => {
  const b = await pr.chromium.launch({ headless: true, channel: "chromium", args: ["--no-sandbox", "--disable-dev-shm-usage"] });
  const ctx = await b.newContext({ viewport: { width: 1440, height: 950 } });
  const p = await ctx.newPage();
  const galat = [];
  p.on("console", m => { if (m.type() === "error") galat.push(m.text().slice(0, 200)); });
  p.on("pageerror", e => galat.push("pageerror: " + String(e).slice(0, 200)));
  p.on("response", r => { if (r.status() >= 500) galat.push(`HTTP ${r.status()} ${r.url().replace(BASE, "")}`); });
  const foto = async nama => { if (LAYAR) await p.screenshot({ path: path.join(LAYAR, nama + ".png"), fullPage: true }); };
  const simpan = async () => Promise.all([p.waitForNavigation(), p.locator("form[data-pengguna-form]").getByRole("button", { name: "Simpan", exact: true }).click()]);
  const opsiTerpilih = async sel => p.$eval(sel, s => s.options[s.selectedIndex].textContent.trim());
  try {
    await p.goto(BASE + "/login/");
    await p.fill("#username", PFX + "admin");
    await p.fill("#password", SANDI);
    await Promise.all([p.waitForNavigation(), p.click("#leTombol")]);
    catat("Login admin", !p.url().includes("/login"), p.url());
    await p.click('aside#sidebar a.sidebar-link[href="/pengguna/"]', { force: true });
    await p.waitForURL(/\/pengguna\/$/);
    catat("Menu Pengguna aktif", await p.locator('aside#sidebar a.sidebar-link.active[href="/pengguna/"]').count() > 0);

    await p.goto(BASE + "/organisasi/");
    await p.click('[data-org-toggle="open"]');
    await Promise.all([p.waitForNavigation(), p.click('a[aria-label="Tambah pengguna di Kepala Seksi HRD"]')]);
    catat("Unit terpilih dari pohon", (await opsiTerpilih("#id_unit")).endsWith("Kepala Seksi HRD"), await opsiTerpilih("#id_unit"));
    await p.check("#id_kepala");
    catat("Jabatan kepala otomatis", await p.inputValue("#id_position") === "Kepala Seksi HRD", await p.inputValue("#id_position"));
    catat("Peran kepala otomatis", await p.inputValue("#id_role") === "KEPALA_UNIT", await p.inputValue("#id_role"));
    await p.fill("#id_first_name", "Hana Kepala HRD");
    await p.fill("#id_username", "e2e_hana");
    await p.fill("#id_password1", "Sandi-Kuat-E2E-2026");
    await p.fill("#id_password2", "Sandi-Kuat-E2E-2026");
    await foto("pengguna-1-form-kepala");
    await simpan();
    catat("Kepala HRD tersimpan", /\/pengguna\/\d+\/$/.test(new URL(p.url()).pathname), p.url());

    await p.goto(BASE + "/organisasi/");
    await p.click('[data-org-toggle="open"]');
    await Promise.all([p.waitForNavigation(), p.click('a[aria-label="Tambah pengguna di Diklat"]')]);
    catat("Jabatan staf otomatis", await p.inputValue("#id_position") === "Staf Diklat", await p.inputValue("#id_position"));
    catat("Atasan otomatis = kepala HRD", await opsiTerpilih("#id_supervisor") === "Hana Kepala HRD", await opsiTerpilih("#id_supervisor"));
    catat("Info saran tampil", (await p.textContent("#saran-info")).includes("Hana Kepala HRD"));
    await p.fill("#id_position", "Koordinator Diklat");          // ubah manual: tidak boleh ditimpa saat kepala dicentang/dilepas
    await p.check("#id_kepala"); await p.uncheck("#id_kepala");
    catat("Isian manual tidak ditimpa", await p.inputValue("#id_position") === "Koordinator Diklat");
    await p.fill("#id_first_name", "Dodi Staf Diklat");
    await p.fill("#id_username", "e2e_dodi");
    await p.fill("#id_password1", "Sandi-Kuat-E2E-2026");
    await p.fill("#id_password2", "Sandi-Kuat-E2E-2026");
    await foto("pengguna-2-form-staf");
    await simpan();
    catat("Staf Diklat tersimpan", /\/pengguna\/\d+\/$/.test(new URL(p.url()).pathname), p.url());

    await p.goto(BASE + "/pengguna/");
    const isi = await p.textContent("#workspace");
    catat("Daftar per bidang", isi.includes("Kepala Bidang Umum & Kepegawaian") && isi.includes("Dodi Staf Diklat"));
    await foto("pengguna-3-daftar");
    await p.goto(BASE + "/organisasi/");
    catat("Kepala tampil di pohon", (await p.textContent("#workspace")).includes("Hana Kepala HRD"));
    await foto("pengguna-4-pohon");

    await p.setViewportSize({ width: 390, height: 844 });
    for (const u of ["/pengguna/", "/pengguna/baru/", "/organisasi/"]) {
      await p.goto(BASE + u);
      const lebar = await p.evaluate(() => document.documentElement.scrollWidth);
      catat(`HP 390px tanpa scroll samping ${u}`, lebar <= 392, `scrollWidth=${lebar}`);
    }
    await foto("pengguna-5-hp");
    catat("Tanpa console error / 5xx", galat.length === 0, galat.join(" | "));
  } catch (e) {
    console.log("GAGAL: " + e.message);
    await foto("pengguna-gagal");
    await b.close();
    process.exit(1);
  }
  await b.close();
})();
