#!/usr/bin/env node
// Uji end-to-end LAPIS 2b: ALUR PENUH di browser (termasuk POST), dijalankan oleh test_alur.py terhadap
// LiveServer Django dengan DATABASE TEST terpisah — bukan DB dev, sehingga POST aman.
//   E2E_SANDI=... node tools/e2e/browser/alur.cjs --base http://localhost:PORT --prefix e2e_ [--layar DIR]
// Skenario PRD 18.4 C no. 1: Direktur membuat & menerbitkan instruksi -> PIC menerima, melapor progres,
// mengunggah bukti, mengirim -> Direktur memverifikasi -> kartu dashboard "Selesai" membuka daftar yang memuat tugas.
const fs = require("fs"), path = require("path"), os = require("os");
const arg = (n, b) => { const i = process.argv.indexOf(n); return i > 0 ? process.argv[i + 1] : b; };
const pr = require("./_patchright.cjs")();
if (!pr) { console.error("patchright tidak ditemukan"); process.exit(2); }
const BASE = arg("--base"), PFX = arg("--prefix", "e2e_"), SANDI = process.env.E2E_SANDI, LAYAR = arg("--layar", "");
if (!BASE || !SANDI) { console.error("--base dan env E2E_SANDI wajib"); process.exit(2); }
if (LAYAR) fs.mkdirSync(LAYAR, { recursive: true });

const langkah = [];
const catat = (nama, ok, pesan = "") => { langkah.push({ nama, ok }); console.log(`[${ok ? "OK   " : "GAGAL"}] ${nama}${pesan ? " — " + pesan : ""}`); if (!ok) throw new Error(nama + ": " + pesan); };
const hariIni = (n = 0) => { const d = new Date(Date.now() + n * 864e5); return d.toLocaleDateString("sv-SE", { timeZone: "Asia/Jakarta" }); };

(async () => {
  const b = await pr.chromium.launch({ headless: true, channel: "chromium", args: ["--no-sandbox", "--disable-dev-shm-usage"] });
  const ctx = await b.newContext({ viewport: { width: 1440, height: 950 } });
  const p = await ctx.newPage();
  const galat = [];
  p.on("console", m => { if (m.type() === "error") galat.push(m.text().slice(0, 200)); });
  p.on("pageerror", e => galat.push("pageerror: " + String(e).slice(0, 200)));
  p.on("response", r => { if (r.status() >= 500) galat.push(`HTTP ${r.status()} ${r.url().replace(BASE, "")}`); });
  p.on("dialog", d => d.accept());          // konfirmasi data-confirm (terbitkan, kirim hasil)
  const foto = async nama => { if (LAYAR) await p.screenshot({ path: path.join(LAYAR, nama + ".png"), fullPage: true }); };
  const kirim = async (selForm, teksTombol) => {
    await Promise.all([p.waitForLoadState("load"), p.waitForNavigation(), p.locator(selForm).getByRole("button", { name: teksTombol }).click()]);
  };
  const masuk = async user => {
    await ctx.clearCookies();
    await p.goto(BASE + "/login/");
    await p.fill("#username", PFX + user);
    await p.fill("#password", SANDI);
    await Promise.all([p.waitForNavigation(), p.click("#leTombol")]);
    catat(`Login ${PFX + user}`, !p.url().includes("/login"), p.url());
  };
  const judul = "E2E Browser Audit troli emergensi";
  try {
    // 1. Direktur: buat draf instruksi, tambah penerima, terbitkan
    await masuk("direktur");
    await p.click('aside#sidebar a.sidebar-link[href="/instruksi/"]', { force: true });
    await p.waitForURL(/\/instruksi\/$/);
    await Promise.all([p.waitForNavigation(), p.getByRole("link", { name: "+ Instruksi baru" }).click()]);
    await p.fill("#id_title", judul);
    await p.fill("#id_description", "Periksa kelengkapan troli emergensi seluruh ruangan.");
    await p.fill("#id_instruction_date", hariIni());
    await p.fill("#id_due_date", hariIni(3));
    await p.selectOption("#id_priority", "TINGGI");
    await p.fill("#id_completion_criteria", "Checklist + foto troli");
    await kirim("#workspace form", "Simpan draf");
    catat("Draf instruksi tersimpan", /\/instruksi\/\d+\/$/.test(new URL(p.url()).pathname), p.url());
    const urlIns = p.url();
    const fTarget = 'form[action$="/penerima/"]';
    // pilih unit & PIC secara TEPAT (nama tampilan akun e2e = username, kode unit berawalan prefix)
    const opsi = async nama => p.$$eval(`${fTarget} [name=${nama}] option`, os => os.map(o => ({ v: o.value, t: o.textContent.trim() })));
    const unit = (await opsi("unit")).find(o => o.t.startsWith(PFX.toUpperCase() + "FARM "));
    const pic = (await opsi("pic")).find(o => o.t === PFX + "staf_farmasi");
    if (!unit || !pic) catat("Opsi unit/PIC e2e tersedia", false, JSON.stringify({ unit, pic }));
    await p.selectOption(`${fTarget} [name=unit]`, unit.v);
    await p.selectOption(`${fTarget} [name=pic]`, pic.v);
    await kirim(fTarget, "Tambah");
    catat("Penerima ditambahkan", (await p.locator("table").first().innerText()).includes(pic.t.trim()), pic.t);
    await kirim('form[action$="/terbitkan/"]', "Terbitkan");
    catat("Instruksi terbit", (await p.innerText("h1")).includes("Diterbitkan"));
    await foto("1-instruksi-terbit");

    // 2. PIC: lihat tugas, terima, progres, unggah bukti, kirim
    await masuk("staf_farmasi");
    await p.goto(BASE + "/tugas/");
    await Promise.all([p.waitForNavigation(), p.getByRole("link", { name: new RegExp(judul) }).click()]);
    const urlTugas = p.url();
    await kirim('form[action$="/terima/"]', "Terima tugas");
    catat("Tugas diterima", (await p.innerText("#workspace")).includes("Belum dimulai"));
    const fProg = 'form[action$="/progres/"]';
    await p.fill(`${fProg} [name=progress]`, "70");
    await p.selectOption(`${fProg} [name=status]`, "BERJALAN");
    await p.fill(`${fProg} [name=note]`, "Ruang IGD & ICU selesai");
    await kirim(fProg, "Simpan progres");
    catat("Progres tersimpan", (await p.innerText("#workspace")).includes("Ruang IGD & ICU selesai"));
    const bukti = path.join(os.tmpdir(), "e2e-bukti-troli.pdf");
    fs.writeFileSync(bukti, "%PDF-1.4 bukti uji e2e browser");
    const fBukti = 'form[action$="/bukti/"]';
    await p.setInputFiles(`${fBukti} [name=file]`, bukti);
    await p.fill(`${fBukti} [name=description]`, "Checklist troli");
    await kirim(fBukti, "Unggah");
    catat("Bukti terunggah", (await p.innerText("#workspace")).includes("e2e-bukti-troli.pdf"));
    await kirim('form[action$="/kirim/"]', /Kirim/);
    catat("Hasil dikirim untuk verifikasi", (await p.innerText("#workspace")).includes("Menunggu verifikasi"));
    await foto("2-pic-kirim");

    // 3. Direktur: verifikasi, lalu dashboard -> kartu Selesai -> daftar memuat tugas
    await masuk("direktur");
    await p.goto(urlTugas);
    await p.selectOption('form[action$="/verifikasi/"] [name=decision]', "approve");
    await kirim('form[action$="/verifikasi/"]', "Simpan keputusan");
    catat("Tugas diverifikasi & selesai", (await p.innerText("#workspace")).includes("Selesai"));
    await p.goto(BASE + "/");
    const kartu = p.locator('a[href="/tugas/?status=SELESAI"]');
    const angka = (await kartu.innerText()).match(/\d+/)[0];
    catat("Dashboard: kartu Selesai = 1", angka === "1", "angka " + angka);
    await Promise.all([p.waitForNavigation(), kartu.click()]);
    catat("Kartu membuka daftar terfilter berisi tugas", (await p.innerText("#workspace")).includes(judul));
    await foto("3-dashboard-daftar");
    await p.goto(urlIns);
    catat("Status baca penerima tercatat", !(await p.innerText("table")).includes("Belum"));
    catat("Tanpa console error / HTTP 5xx", galat.length === 0, galat.slice(0, 3).join(" | "));
  } catch (e) {
    if (!langkah.length || langkah[langkah.length - 1].ok) console.log("[GAGAL] " + String(e).split("\n")[0]);
    await foto("gagal");
    await b.close();
    process.exit(1);
  }
  await b.close();
  console.log(`\n${langkah.length} langkah lolos`);
  process.exit(0);
})();
