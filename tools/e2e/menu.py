"""Inventaris yang diuji: menu sidebar (dibaca dari templat) dan semua rute bernama Django."""
import re
from pathlib import Path

from tools.e2e import _dasar  # noqa: F401  (django.setup)

from django.urls import URLPattern, URLResolver, get_resolver, reverse

AKAR = _dasar.AKAR
SIDEBAR = Path(AKAR) / "templates" / "partials" / "_sidebar_menu.html"
_RE_LINK = re.compile(r"""\{%\s*url\s+'([\w:]+)'\s*%\}"[^>]*aria-label="([^"]+)\"""")


def sidebar():
    """[{nama, label, url}] dari partials/_sidebar_menu.html (urutan tampil, tanpa duplikat)."""
    out, lihat = [], set()
    for nama, label in _RE_LINK.findall(SIDEBAR.read_text(encoding="utf-8")):
        if nama not in lihat:
            lihat.add(nama)
            out.append({"nama": nama, "label": label, "url": reverse(nama)})
    return out


def _jelajah(pola, awalan="", ns=None):
    for p in pola:
        if isinstance(p, URLResolver):
            sub_ns = ":".join(x for x in (ns, p.namespace) if x) or None
            yield from _jelajah(p.url_patterns, awalan + str(p.pattern), sub_ns)
        elif isinstance(p, URLPattern):
            nama = f"{ns}:{p.name}" if ns and p.name else p.name
            teks = awalan + str(p.pattern)
            yield {"nama": nama, "pola": teks, "param": bool(re.search(r"<[^>]+>|\(\?P<", teks))}


def rute():
    """Semua rute bernama: [{nama, pola, param}]."""
    return [r for r in _jelajah(get_resolver().url_patterns) if r["nama"]]


def modul_dari_url(url):
    bagian = [x for x in url.strip("/").split("/") if x]
    return bagian[0] if bagian else "dashboard"
