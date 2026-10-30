"""Registri skenario e2e. Setiap modul di paket ini mendaftarkan skenarionya dengan `@skenario(...)`
atau `daftar(...)` (untuk skenario yang dibangkitkan otomatis), lalu `muat()` mengimpor semuanya.

    @skenario("instruksi", "Instruksi: buat → terbit → tugas", menu=["instructions:create"], crud=True)
    def _(u):
        u.get("/instruksi/baru/")
        ...

`menu` = nama URL (`app:nama`) yang dibuktikan skenario ini -> dipakai `katalog.py` untuk laporan
cakupan; `crud=True` = skenario membuktikan simpan/ubah/hapus (bukan hanya membuka halaman).
`role` = peran awal di dunia QA (direktur, sekretaris, wadir, ka_igd, staf_igd, ka_farmasi, staf_farmasi, auditor).
"""
import importlib
import pkgutil
from dataclasses import dataclass, field


@dataclass
class Skenario:
    modul: str
    nama: str
    fn: object
    menu: list = field(default_factory=list)
    crud: bool = False
    lambat: bool = False
    role: str = "direktur"
    otomatis: bool = False


DAFTAR = []


def daftar(modul, nama, fn, menu=(), crud=False, lambat=False, role="direktur", otomatis=False):
    DAFTAR.append(Skenario(modul, nama, fn, list(menu), crud, lambat, role, otomatis))


def skenario(modul, nama, menu=(), crud=False, lambat=False, role="direktur"):
    def deco(fn):
        daftar(modul, nama, fn, menu, crud, lambat, role)
        return fn
    return deco


_SUDAH = False


def muat():
    global _SUDAH
    if not _SUDAH:
        for m in pkgutil.iter_modules(__path__):
            importlib.import_module(f"{__name__}.{m.name}")
        _SUDAH = True
    return DAFTAR
