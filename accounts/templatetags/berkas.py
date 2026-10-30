import os

from django import template

from accounts.files import bisa_dilihat

register = template.Library()


@register.filter
def jenis_pratinjau(nama):
    """'pdf' / 'gambar' bila berkas bisa ditampilkan di browser, '' bila harus diunduh (Word, Excel)."""
    if not bisa_dilihat(nama):
        return ""
    return "pdf" if os.path.splitext(nama)[1].lower() == ".pdf" else "gambar"


@register.inclusion_tag("_berkas.html")
def tombol_berkas(url, nama, label=""):
    """Tombol Lihat (tab baru, PDF/gambar saja) + Unduh untuk satu berkas."""
    return {"url": url, "nama": nama, "label": label or os.path.basename(nama), "jenis": jenis_pratinjau(nama)}


@register.inclusion_tag("_pratinjau.html")
def pratinjau_berkas(url, nama):
    """Berkas ditampilkan langsung di halaman (PDF dalam bingkai, gambar sebagai gambar)."""
    return {"url": url, "nama": nama, "jenis": jenis_pratinjau(nama)}
