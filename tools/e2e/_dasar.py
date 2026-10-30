"""Kerangka uji end-to-end LAPIS 1 (Django test client, tanpa browser) — pola sama dengan casemix.

Setiap skenario berjalan di dalam `Penjaga`:
- transaksi DB `default` (DB dev E-Office) dibuka lalu SELALU di-rollback -> simpan/ubah/hapus sungguhan
  dijalankan, tetapi tidak ada yang tertinggal (semua tabel E-Office InnoDB; tabel non-InnoDB tetap diblokir
  sebagai jaga-jaga);
- DDL (CREATE/ALTER/DROP/TRUNCATE = commit implisit MySQL) DIBLOKIR;
- berkas unggahan diarahkan ke direktori sementara (MEDIA_ROOT) yang dihapus setelah skenario;
- hasher password cepat untuk akun QA (dibuang bersama rollback);
- koneksi jaringan selain DB/Redis lokal DIBLOKIR (layanan luar di masa depan: email/WhatsApp);
- `Task.apply_async`/`delay` Celery dicatat, tidak dikirim ke broker (Redis host dipakai aplikasi lain).
Data uji = dunia sintetis berawalan QA (`World("qa_")`) yang dibuat di dalam transaksi tiap skenario.
Skrip MENOLAK jalan dengan settings produksi.
"""
import os
import re
import socket
import sys
import tempfile
import time
import traceback
from contextlib import ExitStack
from unittest import mock

AKAR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if AKAR not in sys.path:
    sys.path.insert(0, AKAR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.db import connections, transaction  # noqa: E402
from django.test import Client, override_settings  # noqa: E402

for _h in ("testserver", "localhost"):
    if _h not in settings.ALLOWED_HOSTS:
        settings.ALLOWED_HOSTS = [*settings.ALLOWED_HOSTS, _h]

ALIAS = ("default",)
PREFIX_UJI = "qa_"


class TulisDiblokir(Exception):
    """Tulis yang tidak bisa di-rollback (non-InnoDB / DDL)."""


class JaringanDiblokir(ConnectionRefusedError):
    """Koneksi ke layanan luar saat uji. Turunan ConnectionRefusedError -> klien HTTP melihatnya sebagai koneksi
    gagal biasa, sehingga yang diuji = cara aplikasi menangani layanan luar yang mati."""


class GagalUji(AssertionError):
    pass


def pastikan_dev():
    modul = os.environ.get("DJANGO_SETTINGS_MODULE", "")
    if modul.endswith(".prod") or not settings.DEBUG:
        sys.exit(f"TOLAK: settings '{modul}' (DEBUG={settings.DEBUG}). Uji e2e hanya boleh di DB pengembangan.")


_NON_INNODB = {}


def tabel_non_innodb(alias):
    if alias not in _NON_INNODB:
        if connections[alias].vendor != "mysql":
            _NON_INNODB[alias] = set()
        else:
            with connections[alias].cursor() as c:
                c.execute("SELECT LOWER(table_name) FROM information_schema.tables WHERE table_schema=DATABASE() "
                          "AND table_type='BASE TABLE' AND engine<>'InnoDB'")
                _NON_INNODB[alias] = {r[0] for r in c.fetchall()}
    return _NON_INNODB[alias]


_RE_DML = re.compile(
    r"^\s*(?:INSERT(?:\s+IGNORE)?\s+INTO|REPLACE\s+INTO|UPDATE(?:\s+IGNORE)?|DELETE\s+FROM)\s+`?(\w+)`?", re.I)
_RE_DDL = re.compile(r"^\s*(CREATE(?!\s+TEMPORARY)|ALTER|DROP(?!\s+TEMPORARY)|TRUNCATE|RENAME)\b", re.I)


def _host_lokal():
    izin = {"127.0.0.1", "::1", "localhost"}
    for d in settings.DATABASES.values():
        h = d.get("HOST") or "localhost"
        izin.add(h)
        try:
            izin.update(a[4][0] for a in socket.getaddrinfo(h, None))
        except OSError:
            pass
    return izin


class Penjaga:
    """Context manager: transaksi rollback + blokir tulis tak-terbalikkan + media sementara + blokir jaringan/Celery."""

    def __init__(self):
        self.tulis = {}            # (alias, tabel) -> jumlah pernyataan
        self.celery = []           # nama task yang "dikirim"
        self.jaringan = []         # host yang dicoba
        self._stack = None

    def _pembungkus(self, alias):
        non = tabel_non_innodb(alias)

        def bungkus(execute, sql, params, many, context):
            teks = sql if isinstance(sql, str) else str(sql)
            if _RE_DDL.match(teks):
                raise TulisDiblokir(f"DDL di {alias} (commit implisit, tidak bisa di-rollback): {teks[:120]}")
            m = _RE_DML.match(teks)
            if m:
                tabel = m.group(1).lower()
                if tabel in non:
                    raise TulisDiblokir(f"tulis ke tabel non-InnoDB {alias}.{tabel} (tidak bisa di-rollback)")
                k = (alias, tabel)
                self.tulis[k] = self.tulis.get(k, 0) + 1
            return execute(sql, params, many, context)
        return bungkus

    def __enter__(self):
        izin = _host_lokal()
        asli = socket.socket.connect
        jejak = self.jaringan

        def connect(sock, alamat):
            host = alamat[0] if isinstance(alamat, tuple) else str(alamat)
            if isinstance(alamat, tuple) and host not in izin:
                jejak.append(f"{host}:{alamat[1]}")
                raise JaringanDiblokir(f"koneksi luar {host}:{alamat[1]} diblokir saat uji e2e")
            return asli(sock, alamat)

        def kirim_task(task, *a, **kw):
            self.celery.append(getattr(task, "name", str(task)))
            return mock.Mock(id="e2e-task")

        s = ExitStack()
        media = s.enter_context(tempfile.TemporaryDirectory(prefix="eoffice-e2e-media-"))
        s.enter_context(override_settings(MEDIA_ROOT=media))
        # akun QA dibuat & dibuang tiap skenario: hasher cepat (PBKDF2 = ±0,5 dtk per akun)
        s.enter_context(override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"]))
        for a in ALIAS:
            s.enter_context(transaction.atomic(using=a))
        for a in ALIAS:
            s.enter_context(connections[a].execute_wrapper(self._pembungkus(a)))
        s.enter_context(mock.patch.object(socket.socket, "connect", connect))
        s.enter_context(mock.patch("celery.app.task.Task.apply_async", kirim_task))
        self._stack = s.__enter__()
        return self

    def __exit__(self, *exc):
        for a in ALIAS:
            transaction.set_rollback(True, using=a)
        return self._stack.__exit__(*exc)


# --------------------------------------------------------------------------- klien uji
class Uji:
    """Dipakai di dalam fungsi skenario: `u.sebagai(...)`, `u.get(...)`, `u.post(...)`, `u.harap(...)`.

    `u.w` = dunia QA (unit & akun per peran, lihat testutils.factories.World). Setiap skenario mulai login
    sebagai `role` (default "direktur"); ganti pengguna dengan `u.sebagai("staf_igd")`.
    """

    def __init__(self, penjaga, role="direktur"):
        from testutils.factories import World

        self.p = penjaga
        self.w = World(PREFIX_UJI)
        self.c = Client(enforce_csrf_checks=True, HTTP_HOST="localhost")
        self.langkah = []          # (metode, url, status, ms)
        self.diketahui = []        # (url, masih_gagal) untuk URL di tools/e2e/diketahui.py
        self.catatan = []
        self.pengguna = None
        self.sebagai(role)

    def sebagai(self, peran):
        self.pengguna = getattr(self.w, peran)
        self.c.logout()
        self.c.force_login(self.pengguna)
        return self.pengguna

    def keluar(self):
        self.c.logout()
        self.pengguna = None

    # -- HTTP
    def _catat(self, metode, url, r, t0):
        self.langkah.append((metode, url, r.status_code, int((time.time() - t0) * 1000)))

    @staticmethod
    def teks(r):
        jenis = r.get("Content-Type", "")
        if any(x in jenis for x in ("html", "json", "text")) and not getattr(r, "streaming", False):
            return r.content.decode(errors="ignore")
        return ""

    def _periksa(self, metode, url, r, harap, ada, tidak_ada=()):
        from tools.e2e.diketahui import DIKETAHUI

        jalur = url.split("?")[0]
        try:
            lok = r.get("Location", "")
            if "/login" in lok and "login" not in url and self.pengguna is not None:
                raise GagalUji(f"{metode} {url} -> dialihkan ke login (sesi/hak ditolak)")
            if harap and r.status_code not in (harap if isinstance(harap, (tuple, list, set)) else (harap,)):
                raise GagalUji(f"{metode} {url} -> HTTP {r.status_code} (harap {harap})"
                               + (f" -> {lok}" if lok else ""))
            isi = self.teks(r)
            for g in ("Traceback (most recent call last)", "TemplateSyntaxError", "NoReverseMatch",
                      "VariableDoesNotExist"):
                if g in isi:
                    raise GagalUji(f"{metode} {url} -> halaman memuat '{g}'")
            for x in ada or ():
                if x not in isi:
                    raise GagalUji(f"{metode} {url} -> teks '{x}' tidak ditemukan")
            for x in tidak_ada or ():
                if x in isi:
                    raise GagalUji(f"{metode} {url} -> teks '{x}' seharusnya TIDAK tampil")
        except GagalUji:
            if jalur in DIKETAHUI:
                self.diketahui.append((jalur, True))
                return r
            raise
        if jalur in DIKETAHUI:
            self.diketahui.append((jalur, False))
        return r

    @staticmethod
    def _savepoint():
        """Satu savepoint per permintaan: galat DB di satu view di-rollback ke titik ini sehingga permintaan
        berikutnya tetap jalan (tanpa ini: TransactionManagementError berantai)."""
        s = ExitStack()
        for a in ALIAS:
            s.enter_context(transaction.atomic(using=a))
        return s

    def get(self, url, harap=200, ada=(), tidak_ada=(), **kw):
        t0 = time.time()
        with self._savepoint():
            r = self.c.get(url, **kw)
        self._catat("GET", url, r, t0)
        return self._periksa("GET", url, r, harap, ada, tidak_ada)

    def post(self, url, data=None, harap=(200, 302), ada=(), tidak_ada=(), dari=None, **kw):
        """POST dengan token CSRF dari cookie (GET `dari` — atau dashboard — dulu bila belum ada cookie)."""
        if settings.CSRF_COOKIE_NAME not in self.c.cookies:
            self.c.get(dari or "/")
        tok = self.c.cookies.get(settings.CSRF_COOKIE_NAME)
        data = dict(data or {})
        data.setdefault("csrfmiddlewaretoken", tok.value if tok else "")
        t0 = time.time()
        with self._savepoint():
            r = self.c.post(url, data, **kw)
        self._catat("POST", url, r, t0)
        return self._periksa("POST", url, r, harap, ada, tidak_ada)

    @staticmethod
    def pesan(r):
        """Pesan Django messages pada respons terakhir yang dirender (setelah follow=True)."""
        return [str(m) for m in r.context["messages"]] if getattr(r, "context", None) else []

    # -- asersi
    @staticmethod
    def harap(kondisi, pesan):
        if not kondisi:
            raise GagalUji(pesan)


def jalankan_satu(sk):
    """-> dict hasil satu skenario (selalu rollback)."""
    t0 = time.time()
    hasil = {"nama": sk.nama, "modul": sk.modul, "ok": False, "pesan": "", "langkah": [], "tulis": {},
             "celery": [], "jaringan": []}
    try:
        with Penjaga() as p:
            u = Uji(p, role=sk.role)
            try:
                sk.fn(u)
                hasil["ok"] = True
            finally:
                hasil["langkah"] = u.langkah
                hasil["diketahui"] = u.diketahui
                hasil["catatan"] = list(u.catatan)
                hasil["tulis"] = {f"{a}.{t}": n for (a, t), n in p.tulis.items() if t != "django_session"}
                hasil["celery"], hasil["jaringan"] = p.celery, p.jaringan
    except GagalUji as e:
        hasil["pesan"] = str(e)
    except (TulisDiblokir, JaringanDiblokir) as e:
        hasil["pesan"] = f"{type(e).__name__}: {e}"
    except Exception as e:  # noqa: BLE001
        tb = traceback.extract_tb(e.__traceback__)
        milik = [f for f in tb if AKAR in f.filename and "/.venv/" not in f.filename]
        di = f" @ {os.path.relpath(milik[-1].filename, AKAR)}:{milik[-1].lineno}" if milik else ""
        hasil["pesan"] = f"{type(e).__name__}: {str(e)[:300]}{di}"
    hasil["ms"] = int((time.time() - t0) * 1000)
    return hasil
