"""Skenario yang DIBANGKITKAN otomatis dari inventaris (tidak perlu ditulis tangan):
- setiap menu sidebar dibuka sebagai Direktur (HTTP 200) + setiap tautan internal di halaman itu diikuti;
- setiap rute bernama TANPA parameter dibuka sebagai setiap peran QA: tidak boleh 5xx/Traceback, tidak boleh
  dialihkan ke login (pengguna sudah masuk). 403/404/405 sah (hak akses/khusus POST).
"""
import re

from django.urls import Resolver404, resolve

from accounts.models import Role
from testutils.factories import user

from tools.e2e import menu as M
from tools.e2e._dasar import GagalUji

from . import daftar

# Rute yang tidak dijelajah otomatis: admin Django (punya uji sendiri), logout (mengakhiri sesi), healthz (non-HTML).
LEWATI = re.compile(r"^/(admin/|logout/|healthz)")
SAH = (200, 302, 403, 404, 405)
PERAN = ("direktur", "sekretaris", "wadir", "ka_igd", "staf_igd", "ka_farmasi", "staf_farmasi", "auditor", "arsip")
_RE_HREF = re.compile(r'href="(/[^"#]*)"')


def _rute_tanpa_param():
    return [r for r in M.rute() if not r["param"] and not LEWATI.search("/" + r["pola"])]


def _buat_rute(peran):
    def fn(u):
        for r in _rute_tanpa_param():
            res = u.get("/" + r["pola"], harap=SAH)
            u.harap(res.status_code != 302 or "/login" not in res.get("Location", ""),
                    f"{r['nama']} mengalihkan {peran} ke login")
    return fn


# Menu yang hanya tampil untuk peran tertentu: dijelajah sebagai peran itu (peran lain cukup tidak 5xx, lihat _buat_rute).
MENU_PERAN = {"pengguna:index": Role.ADMIN, "pengaturan:index": Role.ADMIN}


def _buat_menu(item):
    def fn(u):
        if item["nama"] in MENU_PERAN:
            u.w.khusus = user(MENU_PERAN[item["nama"]], unit=u.w.dir_unit, username="qa_menu_khusus")
            u.sebagai("khusus")
        r = u.get(item["url"], harap=200)
        tautan = sorted({h for h in _RE_HREF.findall(u.teks(r)) if not LEWATI.search(h) and "/static/" not in h})
        dicek = 0
        for h in tautan[:40]:
            try:
                resolve(h.split("?")[0])
            except Resolver404:
                raise GagalUji(f"tautan mati di {item['url']}: {h}")
            u.get(h, harap=SAH)
            dicek += 1
        u.catatan.append(f"{item['label']}: {dicek} tautan diikuti")
    return fn


for _peran in PERAN:
    daftar("otomatis", f"Semua rute tanpa parameter sebagai {_peran}", _buat_rute(_peran), role=_peran,
           otomatis=True, lambat=_peran not in ("direktur", "staf_igd", "auditor"))

for _item in M.sidebar():
    if LEWATI.search(_item["url"]):      # menu Administrasi = admin Django, hanya untuk staf teknis
        continue
    daftar("otomatis", f"Menu {_item['label']} + tautan di halamannya", _buat_menu(_item),
           menu=[_item["nama"]], otomatis=True)
