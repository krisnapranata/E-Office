#!/usr/bin/env python3
"""Katalog cakupan uji e2e: menu & rute aplikasi vs skenario yang membuktikannya (pola casemix).

    .venv/bin/python tools/e2e/katalog.py                 # ringkasan cakupan per modul
    .venv/bin/python tools/e2e/katalog.py --cek           # GAGAL (exit 1) bila ada menu/rute BARU tanpa skenario
    .venv/bin/python tools/e2e/katalog.py --perbarui-baku # catat yang belum tercakup sekarang sebagai backlog (baku.json)
    .venv/bin/python tools/e2e/katalog.py --rencana       # tulis FILE BARU docs/rencana-uji/<tanggal>-rencana-e2e.md
    .venv/bin/python tools/e2e/katalog.py --json f.json   # inventaris lengkap

Aturan cakupan:
- menu sidebar   : tercakup GET otomatis; "CRUD" bila ada skenario `crud=True` dengan `menu=[nama]`;
                   menu di HANYA_BACA cukup punya skenario (tanpa crud).
- rute bernama   : tercakup bila tanpa parameter (dijelajah otomatis untuk semua peran), atau disebut di
                   `menu=[...]` sebuah skenario.
- `baku.json`    : backlog yang SUDAH diketahui belum tercakup. Yang tidak tercakup DAN tidak ada di baku =
                   menu/rute baru -> `--cek` gagal -> wajib tulis skenario (skill uji-e2e).
"""
import argparse
import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.e2e import menu as M  # noqa: E402
from tools.e2e.skenario import muat  # noqa: E402
from tools.e2e.skenario.otomatis import LEWATI  # noqa: E402

BAKU = Path(__file__).with_name("baku.json")
RENCANA = Path(M.AKAR) / "docs" / "rencana-uji"
LEWAT_RUTE = ("admin/",)        # admin Django: bawaan framework, akses dibatasi is_staff
# Menu yang memang HANYA-BACA (tidak ada simpan/ubah/hapus): cukup dibuktikan skenario non-CRUD.
# Menambah menu ke sini = keputusan sadar bahwa halaman itu tidak menulis data; tetap wajib punya skenario.
HANYA_BACA = {"dashboard:home", "panduan:index"}

# Alur kritis PRD 18.4 C -> skenario yang membuktikannya (dipakai di rencana).
SKENARIO_PRD = [
    (1, "Instruksi sampai penutupan", "instruksi", "Instruksi → PIC terima"),
    (2, "Surat dan disposisi", "surat", "Surat masuk → disposisi"),
    (3, "Keputusan rapat", None, "Tahap 2 (E-Notulen belum ada)"),
    (4, "Reminder H-2", "reminder", "H-2"),
    (5, "Terlambat dan eskalasi", "reminder", "Terlambat"),
    (6, "Perlu perbaikan", "tugas", "perlu perbaikan"),
    (7, "Permission dan kerahasiaan", "akses", ""),
    (8, "Audit trail", "tugas", "audit trail"),
    (9, "Filter dashboard", "dashboard", ""),
    (10, "Kegagalan notifikasi", "reminder", "Kanal gagal"),
]


def inventaris():
    sk = muat()
    side = [x for x in M.sidebar() if not LEWATI.search(x["url"])]
    rute = [r for r in M.rute() if not r["pola"].startswith(LEWAT_RUTE)]
    disebut = {m for s in sk for m in s.menu}
    crud = {m for s in sk if s.crud for m in s.menu}
    rt = []
    for r in rute:
        if r["nama"] in disebut:
            cara = "skenario"
        elif not r["param"] and not LEWATI.search("/" + r["pola"]):
            cara = "otomatis (tanpa parameter)"
        else:
            cara = ""
        rt.append({**r, "modul": M.modul_dari_url("/" + r["pola"]), "cara": cara, "crud": r["nama"] in crud})
    mn = [{**x, "modul": M.modul_dari_url(x["url"]), "crud": x["nama"] in crud,
           "skenario": [s.nama for s in sk if x["nama"] in s.menu]} for x in side]
    return {"sidebar": mn, "rute": rt,
            "skenario": [{"modul": s.modul, "nama": s.nama, "menu": s.menu, "crud": s.crud, "lambat": s.lambat,
                          "otomatis": s.otomatis, "role": s.role} for s in sk]}


def belum(inv):
    return {"sidebar_tanpa_crud": sorted(x["nama"] for x in inv["sidebar"]
                                         if not x["crud"] and not (x["nama"] in HANYA_BACA and x["skenario"])),
            "rute_tanpa_uji": sorted(r["nama"] for r in inv["rute"] if not r["cara"])}


def ringkas(inv):
    print("== Menu sidebar")
    for x in inv["sidebar"]:
        jenis = "CRUD" if x["crud"] else ("BACA" if x["nama"] in HANYA_BACA else "GET ")
        print(f"  {jenis}  {x['label']:24} {x['url']}")
    print("\n== Rute per modul (tercakup / total)")
    per = defaultdict(lambda: [0, 0])
    for r in inv["rute"]:
        per[r["modul"]][1] += 1
        per[r["modul"]][0] += bool(r["cara"])
    for m, (a, b) in sorted(per.items(), key=lambda x: -x[1][1]):
        print(f"  {m:24} {a:4}/{b:<4} {'█' * int(20 * a / b) if b else ''}")
    b = belum(inv)
    tot = len(inv["rute"])
    print(f"\n== Skenario: {len(inv['skenario'])} ({sum(s['crud'] for s in inv['skenario'])} CRUD)")
    print(f"== Rute tercakup {tot - len(b['rute_tanpa_uji'])}/{tot}; menu sidebar dengan CRUD "
          f"{len(inv['sidebar']) - len(b['sidebar_tanpa_crud'])}/{len(inv['sidebar'])}")
    for n in b["rute_tanpa_uji"]:
        print(f"   - belum tercakup: {n}")


def cek(inv):
    if not BAKU.exists():
        print("baku.json belum ada -> jalankan --perbarui-baku sekali.")
        return 1
    baku = json.loads(BAKU.read_text(encoding="utf-8"))
    b = belum(inv)
    baru = {k: sorted(set(v) - set(baku.get(k, []))) for k, v in b.items()}
    lunas = {k: sorted(set(baku.get(k, [])) - set(v)) for k, v in b.items()}
    for k, v in lunas.items():
        if v:
            print(f"  [INFO] {len(v)} {k} kini tercakup (jalankan --perbarui-baku): {', '.join(v[:10])}")
    if any(baru.values()):
        print("  [GAGAL] menu/rute BARU tanpa skenario e2e:")
        for k, v in baru.items():
            for n in v:
                r = next((x for x in inv["rute"] if x["nama"] == n), {})
                print(f"     - {k}: {n}  {('/' + r['pola']) if r else ''}")
        print("  -> tambahkan skenario di tools/e2e/skenario/<modul>.py (skill uji-e2e), lalu jalankan ulang.")
        return 1
    print(f"  [OK] tidak ada menu/rute baru tanpa uji (backlog lama: {len(b['rute_tanpa_uji'])} rute, "
          f"{len(b['sidebar_tanpa_crud'])} menu tanpa CRUD)")
    return 0


def tulis_rencana(inv):
    """Selalu FILE BARU (tidak menimpa): <tanggal>-rencana-e2e.md, -v2, -v3, ... + baris di INDEX.md."""
    RENCANA.mkdir(parents=True, exist_ok=True)
    hari = dt.date.today().isoformat()
    f, n = RENCANA / f"{hari}-rencana-e2e.md", 1
    while f.exists():
        n += 1
        f = RENCANA / f"{hari}-rencana-e2e-v{n}.md"
    sebelumnya = sorted(p.name for p in RENCANA.glob("*-rencana-e2e*.md") if p != f)
    b = belum(inv)
    sk = inv["skenario"]
    L = [f"# Rencana uji end-to-end E-Office — {hari}" + (f" (versi {n})" if n > 1 else ""), "",
         "Dibangkitkan oleh `.venv/bin/python tools/e2e/katalog.py --rencana`. File ini TIDAK diubah lagi; perubahan",
         "berikutnya = file baru (lihat `INDEX.md`)." + (f" Versi sebelumnya: `{sebelumnya[-1]}`." if sebelumnya else ""),
         "", "## 1. Tujuan & cara uji", "",
         "- **Lapis 1 — Django test client** (`tools/e2e/jalankan.py`): semua menu sidebar + tautan di halamannya,",
         "  semua rute tanpa parameter untuk 8 peran, dan alur CRUD tulisan tangan. DB dev, setiap skenario",
         "  di-rollback (dunia QA `qa_*` dibuat di dalam transaksi); DDL & tabel non-InnoDB diblokir; unggahan ke",
         "  direktori sementara; jaringan luar & Celery dicegat.",
         "- **Lapis 2 — browser headless** (`tools/e2e/browser/e2e.cjs`): klik setiap menu sidebar di runserver,",
         "  console error, respons ≥500, lebar HP 390 px. Semua POST dari browser DIBATALKAN.",
         "- **Lapis 2b — alur penuh di browser** (`tools/e2e/browser/test_alur.py` + `alur.cjs`): LiveServer dengan DB",
         "  test terpisah; login → instruksi → PIC → bukti → verifikasi → dashboard, termasuk POST.",
         "- Gerbang: `tools/e2e/katalog.py --cek` gagal bila ada menu/rute baru tanpa skenario.", "",
         "## 2. Inventaris saat ini", "",
         f"- Menu sidebar: **{len(inv['sidebar'])}** ({len(inv['sidebar']) - len(b['sidebar_tanpa_crud'])} dengan CRUD)",
         f"- Rute bernama (tanpa admin/): **{len(inv['rute'])}**, tercakup "
         f"**{len(inv['rute']) - len(b['rute_tanpa_uji'])}**",
         f"- Skenario: **{len(sk)}** ({sum(s['crud'] for s in sk)} CRUD, {sum(s['otomatis'] for s in sk)} otomatis)",
         "", "## 3. Skenario wajib PRD 18.4 C", "", "| No | Skenario | Status | Bukti |", "|---|---|---|---|"]
    for no, nama, modul, kunci in SKENARIO_PRD:
        cocok = [s["nama"] for s in sk if s["modul"] == modul and kunci.lower() in s["nama"].lower()] if modul else []
        status = "✅ lapis 1" if cocok else ("⏸ " + kunci if not modul else "⬜ belum")
        if no == 1:
            status += " + lapis 2b"
        L.append(f"| {no} | {nama} | {status} | {'; '.join(cocok) or '-'} |")
    L += ["", "## 4. Menu sidebar", "", "| Menu | URL | Uji | Skenario |", "|---|---|---|---|"]
    for x in inv["sidebar"]:
        crud = "✅" if x["crud"] else ("hanya-baca" if x["nama"] in HANYA_BACA else "⬜")
        L.append(f"| {x['label']} | `{x['url']}` | GET ✅ · CRUD {crud} | "
                 f"{'; '.join(x['skenario']) or '-'} |")
    L += ["", "## 5. Rute", "", "| Rute | Pola | Cara | CRUD |", "|---|---|---|---|"]
    for r in sorted(inv["rute"], key=lambda r: r["nama"]):
        L.append(f"| `{r['nama']}` | `/{r['pola']}` | {r['cara'] or '⬜ belum'} | {'✅' if r['crud'] else ''} |")
    L += ["", "## 6. Skenario", "", "| Modul | Skenario | Peran awal | CRUD |", "|---|---|---|---|"]
    for s in sk:
        L.append(f"| {s['modul']} | {s['nama']} | {s['role']} | {'✅' if s['crud'] else ''} |")
    L += ["", "## 7. Di luar cakupan / backlog", "",
          "- Skenario no. 3 (keputusan rapat) menunggu modul E-Notulen (Tahap 2).",
          "- Admin Django (`/admin/`) memakai uji bawaan framework; hanya untuk staf teknis.",
          *[f"- Rute belum tercakup: `{n}`" for n in b["rute_tanpa_uji"]], ""]
    f.write_text("\n".join(L), encoding="utf-8")
    idx = RENCANA / "INDEX.md"
    if not idx.exists():
        idx.write_text("# Indeks rencana uji e2e\n\nSetiap baris = satu file rencana (tidak pernah diubah).\n\n",
                       encoding="utf-8")
    with idx.open("a", encoding="utf-8") as fh:
        fh.write(f"- [{f.name}]({f.name}) — {len(sk)} skenario, rute tercakup "
                 f"{len(inv['rute']) - len(b['rute_tanpa_uji'])}/{len(inv['rute'])}\n")
    print("rencana ditulis:", f.relative_to(M.AKAR))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cek", action="store_true")
    ap.add_argument("--perbarui-baku", action="store_true")
    ap.add_argument("--rencana", action="store_true")
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    inv = inventaris()
    if a.json:
        Path(a.json).write_text(json.dumps(inv, ensure_ascii=False, indent=1), encoding="utf-8")
        print("inventaris:", a.json)
        return 0
    if a.perbarui_baku:
        BAKU.write_text(json.dumps(belum(inv), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("baku.json diperbarui:", {k: len(v) for k, v in belum(inv).items()})
        return 0
    if a.cek:
        return cek(inv)
    if a.rencana:
        return tulis_rencana(inv)
    ringkas(inv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
