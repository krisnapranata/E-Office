"""Bantuan bersama skenario (bukan skenario; nama berawalan _ tetap diimpor muat() tetapi tidak mendaftar apa pun)."""
import re
from datetime import timedelta
from html import unescape

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

JUDUL_QA = "QA E2E"


def hari(n=0):
    return (timezone.localdate() + timedelta(days=n)).isoformat()


def berkas(nama="bukti-qa.pdf"):
    return SimpleUploadedFile(nama, b"%PDF-1.4 berkas uji e2e", content_type="application/pdf")


def url(nama, *args):
    return reverse(nama, args=args)


_RE_KARTU = re.compile(
    r'href="/tugas/\?([^"]+)">\s*<div class="card[^"]*"><div class="card-body"><div class="text-muted small">'
    r'([^<]+)</div><div class="fs-3[^"]*">(\d+)</div>')
_RE_JUMLAH = re.compile(r"(\d+) tugas</p>")


def kartu_dashboard(html):
    """[(label, angka, querystring)] dari kartu status tugas di dashboard."""
    return [(unescape(lbl), int(n), unescape(qs)) for qs, lbl, n in _RE_KARTU.findall(html)]


def jumlah_daftar(html):
    m = _RE_JUMLAH.search(html)
    return int(m.group(1)) if m else None
