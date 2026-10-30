"""Halaman Panduan: semua peran dapat membuka, bagian perannya sendiri tampil pertama, tautan tidak mati."""
import re

from django.urls import Resolver404, resolve

from . import skenario
from ._bantu import url

PERAN = ("direktur", "sekretaris", "wadir", "ka_igd", "staf_igd", "ka_farmasi", "staf_farmasi", "auditor", "arsip")


@skenario("panduan", "Panduan per peran: peran sendiri tampil pertama, tautan 'Buka halaman' valid",
          menu=["panduan:index"])
def _(u):
    for peran in PERAN:
        u.sebagai(peran)
        html = u.teks(u.get(url("panduan:index"), ada=["Panduan Penggunaan E-Office", "Alur besar E-Office",
                                                      "Panduan per modul (12 modul)", "Pertanyaan umum"]))
        u.harap(html.count('id="tab-modul-') == 12, f"{peran}: jumlah modul di panduan bukan 12")
        pertama = re.search(r'id="tab-(\w+)"', html).group(1)
        u.harap(pertama == u.pengguna.role, f"{peran}: tab pertama {pertama} (harap {u.pengguna.role})")
        u.harap(html.count(">Anda</span>") == 1, f"{peran}: penanda 'Anda' tidak tepat satu")
        u.harap("{" not in re.sub(r"<script.*?</script>|<style.*?</style>", "", html, flags=re.S)
                .split('id="workspace"')[1].split("</main>")[0], f"{peran}: placeholder belum terisi")
        for h in set(re.findall(r'class="btn btn-sm btn-outline-primary" href="([^"]+)"', html)):  # termasuk "Buka modul"
            try:
                resolve(h)
            except Resolver404:
                u.harap(False, f"{peran}: tautan panduan mati {h}")
            u.get(h, harap=(200, 302))     # admin -> 302 ke login admin untuk non-staf
