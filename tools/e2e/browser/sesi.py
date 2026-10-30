#!/usr/bin/env python3
"""Buat sesi login sementara untuk uji browser lapis 2, lalu hapus (pola mint_session.py casemix).

Skrip browser tidak mengetik kata sandi dan kredensial tidak disimpan di mana pun: skrip ini membuat SATU baris
`django_session` untuk pengguna yang sudah ada (mis. akun demo dari `seed_demo`) dan mencetak session key-nya
untuk disuntikkan sebagai cookie `sessionid`.

    KEY=$(.venv/bin/python tools/e2e/browser/sesi.py --user direktur)
    .venv/bin/python tools/e2e/browser/sesi.py --hapus $KEY

HANYA untuk database pengembangan (menolak settings produksi).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.e2e import _dasar  # noqa: E402  (django.setup)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--user")
    g.add_argument("--hapus")
    a = ap.parse_args()
    _dasar.pastikan_dev()
    from django.conf import settings
    from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY, get_user_model
    from django.contrib.sessions.backends.db import SessionStore
    from django.contrib.sessions.models import Session

    if a.hapus:
        n, _ = Session.objects.filter(session_key=a.hapus).delete()
        print(f"hapus {n} baris sesi {a.hapus[:12]}...", file=sys.stderr)
        return 0
    try:
        u = get_user_model().objects.get(username=a.user, is_active=True)
    except get_user_model().DoesNotExist:
        sys.exit(f"pengguna '{a.user}' tidak ada/aktif (jalankan seed_demo dulu)")
    s = SessionStore()
    s[SESSION_KEY] = str(u.pk)
    s[BACKEND_SESSION_KEY] = settings.AUTHENTICATION_BACKENDS[0]
    s[HASH_SESSION_KEY] = u.get_session_auth_hash()
    s.create()
    print(s.session_key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
