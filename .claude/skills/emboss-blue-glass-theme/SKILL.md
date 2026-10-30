---
name: emboss-blue-glass-theme
description: "Tema \"Emboss Blue Glass (Kaca Biru Timbul)\" E-Office — tema terang kaca biru bermotif EMBOSS: latar biru pucat, panel kaca putih timbul, isian form cekung, tombol timbul, sidebar navy, aksen biru laut; basis blue-glass.css (via @import, yang berbasis mint-forest.css); area kertas tetap putih; halaman login sama dengan casemix. Pakai setiap kali membuat/mengubah template, halaman, komponen UI, CSS, atau halaman login."
---

# Tema Emboss Blue Glass (Kaca Biru Timbul)

Tema **terang** kaca biru dengan motif EMBOSS: latar biru pucat, panel kaca putih **timbul**, isian form **cekung**,
tombol **timbul** (tertekan saat diklik), **sidebar navy**, aksen **biru laut**. Bukan tema gelap; **area kertas tetap putih**.
Diambil dari proyek casemix (`/home/krisna/iDRG/casemix/casemixiDRG/static/css/tema/`) agar tampilan seragam.

## Rantai berkas (urutan cascade WAJIB)
```
templates/base.html
  vendor/bootstrap/bootstrap.min.css
  vendor/bootstrap-icons/bootstrap-icons.css      (+ fonts/*.woff2, lokal)
  css/fonts/google-fonts-inter.css                 (Inter .ttf lokal; Plus Jakarta Sans tidak ada → jatuh ke Inter)
  css/tema/emboss-blue-glass.css   ── @import blue-glass.css ── @import mint-forest.css
  css/app.css                                      (penyesuaian kecil E-Office, dimuat terakhir)
```
- `mint-forest.css` = **tata letak** (sidebar hover-expand, topbar, kartu, tabel, tombol, area kertas).
- `blue-glass.css` = **warna** biru + tambalan.
- `emboss-blue-glass.css` = **lapisan emboss** (bayangan ganda gelap kanan-bawah + putih kiri-atas + kilau tepi).
- Ketiga berkas adalah **salinan** dari casemix. Jangan disunting di E-Office kecuali benar-benar perlu; penyesuaian E-Office masuk `css/app.css`.
  Bila menyinkron ulang dari casemix: salin ketiganya bersamaan lalu verifikasi visual.
- Semua aset **lokal, tanpa CDN** (permintaan pengguna). Jangan menambah `<link>`/`<script>` ke domain luar (termasuk Google Fonts).

## Token utama (di `emboss-blue-glass.css` bagian 1 — ditulis LENGKAP, jangan andalkan berkas basis)
| Token | Nilai | Peran |
|---|---|---|
| `--mc-page` | `#E3EBF5` | latar biru pucat |
| `--mc-surface` | `#FFFFFF` | panel/kertas putih |
| `--mc-primary` / `-hover` | `#0B6BC4` / `#0957A0` | aksen biru laut, tombol utama |
| `--mc-forest` | `#0B3976` | biru tua (judul, ujung gradien sidebar) |
| `--bg-sidebar` | gradien `#11509A → #0E4383 → #0B3976` | sidebar navy |
| `--mc-text` / `--mc-text-muted` | `#17395F` / `#4C6275` | teks (kontras AA terukur) |
| `--mc-focus` | `#1687ED` | cincin fokus |
| `--eb-gelap` / `--eb-gelap-tipis` / `--eb-terang` | rgba biru keabuan / putih | bahan bayangan emboss |
| `--glass-shadow` | `9px 9px 22px gelap, -8px -8px 18px terang, kilau` | **panel timbul** — dipakai `.card/.panel/.glass/.shadow` |

Pakai token (`var(--mc-primary)`), jangan menulis hex baru di template/app.css.

## Kontrak markup shell (selektor tema bergantung padanya)
```html
<html data-bs-theme="light">                       <!-- wajib "light" -->
<body class="page-dense">                          <!-- halaman kerja -->
  <div class="bg-orbs" aria-hidden="true">...</div>
  partials/sidebar.html   → div#mobileSidebar.offcanvas.sidebar.sidebar-mobile  +  aside#sidebar.sidebar.sidebar-desktop.glass
  <div class="content-area app-main">              <!-- efek cekung/timbul diskop ke .content-area -->
    partials/topbar.html  → nav.navbar.custom-navbar.topbar (.topbar-left/.topbar-right, .topbar-btn.glass, .search-box.glass, .profile-dropdown)
    <main id="workspace"> ...konten... </main>
    <footer class="new-footer">...</footer>
  </div>
```
- Link menu: `a.nav-link.sidebar-link` berisi `span.sidebar-icon > i.bi-*` + `span.label`; tambah `active` untuk halaman aktif.
  Kelompok: `div.sidebar-group-title`. Menu didefinisikan sekali di `partials/_sidebar_menu.html` (dipakai desktop & mobile).
- `#sidebarToggle` = pin sidebar (`body.sidebar-pinned`, localStorage `eoffice-sidebar-pinned`; diterapkan dini oleh `js/sidebar-pin-init.js`).
  Perilaku hover/pin/sorot ada di `js/theme-glass.js`.
- Konten: judul `h1.h3`, kelompok isi di `.card` (+ `.card-header` / `.card-body`), tabel `.table` di dalam kartu, form memakai
  `templates/_form.html` (kelas Bootstrap ditambahkan `js/app.js`; form filter ringkas pakai `form.form-compact`).
- Halaman di dalam `#workspace` otomatis mendapat: panel timbul, isian cekung (`.form-control/.form-select` + input tanpa kelas),
  tombol timbul (`.btn` kecuali `.btn-link/.btn-close`), tab aktif timbul, item terpilih cekung.

- Elemen `position: sticky` di konten harus memakai `top` ≥ 84px (topbar tema sticky di 16px, tinggi ±44px); contoh `.panduan-toc`.

## Area kertas — tetap putih
Dokumen/cetak dibungkus salah satu kelas `.paper`, `.document-page`, `.surat-page` (dll., lihat bagian 9 tema).
Di dalamnya **tidak** ada isian cekung maupun tombol timbul, dan `color-scheme: light`. Pakai ini untuk pratinjau surat,
lembar disposisi, atau laporan yang akan dicetak/PDF. Contoh nyata: `notulen/print.html`, `tindaklanjut/cetak.html`,
`laporan/cetak.html` (`<article class="paper">` + tombol `data-print`; aturan `@media print` di `css/app.css`
menyembunyikan sidebar/topbar).

## Halaman login (sama dengan casemix)
- `templates/registration/login.html` — halaman mandiri (tidak extend `base.html`), memuat font, ikon, tema (untuk token), lalu `css/login.css`.
- Latar SVG bertoken `templates/registration/_login_latar.html`; perilaku `js/login.js` (mata password, validasi, "Memeriksa…", cegah kirim ganda).
- Kelas berawalan `le-`; id form WAJIB: `#leForm`, `#username`, `#password`, `#leMata`, `#leTombol` (dipakai login.js & test).
- Galat dari `form.non_field_errors` (LoginView Django). Jangan menambah tombol fitur yang tidak ada (lupa password, SSO, "ingat saya").

## Jangan
- Menulis kata `url` diikuti kurung di **komentar** CSS — manifest collectstatic membacanya sebagai rujukan aset → build Docker gagal.
- Menghapus berkas `.map` di `static/vendor/bootstrap/` (dirujuk oleh CSS/JS; manifest gagal tanpanya).
- Inline `<script>`/`onclick`/`<style>` besar; pakai `static/js/app.js` & `static/css/app.css`.
- Mengunci latar tombol `.btn-outline-*` dengan `!important` di semua keadaan (teks putih hilang saat hover — sudah ditangani tema).
- Memakai `data-bs-theme="dark"` atau warna gelap untuk area konten.

## Verifikasi setelah mengubah UI
1. `.venv/bin/python manage.py runserver 127.0.0.1:8011` (DEBUG menyajikan static).
2. Skill `browser-automation`: login (`#username`/`#password`/`#leTombol`, akun demo dari `seed_demo`), screenshot halaman terkait
   pada 1440×900 dan 390×844; hover `#sidebar` untuk mengecek sidebar melebar. **Lihat gambarnya**, pastikan console error 0 & request gagal 0.
3. Periksa: latar biru pucat, panel putih timbul, isian cekung, tombol timbul, sidebar navy, teks terbaca, tidak ada teks terpotong.
4. Untuk produksi: `docker compose build` harus lulus `collectstatic` (manifest).
