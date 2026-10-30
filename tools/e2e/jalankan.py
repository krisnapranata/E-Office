#!/usr/bin/env python3
"""Jalankan uji end-to-end lapis 1 (Django test client; DB dev, selalu rollback).

    .venv/bin/python tools/e2e/jalankan.py                     # semua skenario cepat
    .venv/bin/python tools/e2e/jalankan.py --semua             # + skenario lambat
    .venv/bin/python tools/e2e/jalankan.py --modul instruksi   # hanya modul tertentu (boleh diulang / koma)
    .venv/bin/python tools/e2e/jalankan.py --cari disposisi    # nama skenario memuat teks
    .venv/bin/python tools/e2e/jalankan.py --daftar            # daftar skenario saja
    .venv/bin/python tools/e2e/jalankan.py --json hasil.json   # simpan rincian (langkah, tabel yang ditulis)
Kode keluar 0 = semua lolos.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.e2e import _dasar  # noqa: E402
from tools.e2e.diketahui import DIKETAHUI  # noqa: E402
from tools.e2e.skenario import muat  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--semua", action="store_true", help="ikutkan skenario lambat")
    ap.add_argument("--modul", action="append", default=[])
    ap.add_argument("--cari", default="")
    ap.add_argument("--daftar", action="store_true")
    ap.add_argument("--json", default="")
    ap.add_argument("--rinci", action="store_true", help="cetak setiap langkah HTTP")
    a = ap.parse_args()
    _dasar.pastikan_dev()
    import logging
    logging.getLogger("django.request").setLevel(logging.CRITICAL)   # 4xx/5xx sudah dilaporkan per skenario
    logging.getLogger("notifications.services").setLevel(logging.CRITICAL)  # kegagalan kirim yang disengaja

    modul = {m.strip() for x in a.modul for m in x.split(",") if m.strip()}
    sk = [s for s in muat()
          if (a.semua or not s.lambat or modul or a.cari)
          and (not modul or s.modul in modul)
          and (a.cari.lower() in s.nama.lower())]
    if a.daftar:
        for s in sk:
            print(f"{s.modul:14} {'CRUD ' if s.crud else '     '}{'lambat ' if s.lambat else ''}{s.nama}")
        print(f"\n{len(sk)} skenario")
        return 0

    t0, hasil = time.time(), []
    for s in sk:
        h = _dasar.jalankan_satu(s)
        hasil.append(h)
        tanda = "OK   " if h["ok"] else "GAGAL"
        tulis = f" · tulis {sum(h['tulis'].values())}x{len(h['tulis'])} tabel (rollback)" if h["tulis"] else ""
        print(f"[{tanda}] {s.modul:12} {s.nama}  ({len(h['langkah'])} langkah, {h['ms']} ms{tulis})", flush=True)
        if not h["ok"]:
            print(f"        {h['pesan']}")
        if a.rinci:
            for m, url, st, ms in h["langkah"]:
                print(f"          {m:4} {st} {ms:5} ms {url}")
        for url, masih in h.get("diketahui", []):
            print(f"        DIKETAHUI {url}: " + (DIKETAHUI[url][1] if masih else
                                                  "SUDAH LOLOS -> hapus barisnya dari tools/e2e/diketahui.py"))
        for c in h.get("catatan", []):
            print(f"        {c}")
        if h["celery"]:
            print(f"        celery dicegat: {', '.join(sorted(set(h['celery'])))}")
        if h["jaringan"]:
            print(f"        jaringan luar dicegat: {', '.join(sorted(set(h['jaringan'])))}")

    lolos = sum(h["ok"] for h in hasil)
    langkah = sum(len(h["langkah"]) for h in hasil)
    print(f"\n{len(hasil)} skenario, {lolos} lolos, {len(hasil) - lolos} gagal · {langkah} permintaan HTTP · "
          f"{round(time.time() - t0, 1)} dtk")
    if a.json:
        Path(a.json).write_text(json.dumps(hasil, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        print("rincian:", a.json)
    return 0 if lolos == len(hasil) else 1


if __name__ == "__main__":
    sys.exit(main())
