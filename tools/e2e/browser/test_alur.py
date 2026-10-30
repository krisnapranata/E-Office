"""Lapis 2b: alur penuh di browser (termasuk POST) terhadap LiveServer dengan DB test terpisah.

Dilewati kecuali E2E_BROWSER=1 (butuh Node + patchright; ±20 dtk):
    E2E_BROWSER=1 DJANGO_SETTINGS_MODULE=config.settings.test \
        .venv/bin/python manage.py test tools.e2e.browser --noinput
Tambahkan E2E_LAYAR=/path/folder untuk menyimpan screenshot setiap tahap.
"""
import os
import secrets
import shutil
import subprocess
from pathlib import Path
from unittest import skipUnless

from django.contrib.auth.hashers import make_password
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from accounts.models import Role, User
from accounts.organisasi import seed_rsiy
from testutils.factories import World, user

SKRIP = Path(__file__).with_name("alur.cjs")
SKRIP_PENGGUNA = Path(__file__).with_name("alur_pengguna.cjs")


@skipUnless(os.environ.get("E2E_BROWSER") == "1" and shutil.which("node"),
            "set E2E_BROWSER=1 (dan pasang node) untuk uji browser")
class AlurBrowserTests(StaticLiveServerTestCase):
    host = "localhost"

    def test_instruksi_sampai_dashboard(self):
        World("e2e_")
        sandi = secrets.token_urlsafe(12)
        for u in User.objects.filter(username__startswith="e2e_"):
            u.first_name, u.last_name, u.password = u.username, "", make_password(sandi)
            u.save()
        cmd = ["node", str(SKRIP), "--base", self.live_server_url, "--prefix", "e2e_"]
        if os.environ.get("E2E_LAYAR"):
            cmd += ["--layar", os.environ["E2E_LAYAR"]]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180,
                           env={**os.environ, "E2E_SANDI": sandi})
        print(r.stdout[-4000:])
        self.assertEqual(r.returncode, 0, r.stdout[-3000:] + r.stderr[-2000:])

    def test_pengguna_dari_pohon_organisasi(self):
        seed_rsiy()
        sandi = secrets.token_urlsafe(12)
        admin = user(Role.ADMIN, username="e2e_admin")
        admin.password = make_password(sandi)
        admin.save()
        cmd = ["node", str(SKRIP_PENGGUNA), "--base", self.live_server_url, "--prefix", "e2e_"]
        if os.environ.get("E2E_LAYAR"):
            cmd += ["--layar", os.environ["E2E_LAYAR"]]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180,
                           env={**os.environ, "E2E_SANDI": sandi})
        print(r.stdout[-4000:])
        self.assertEqual(r.returncode, 0, r.stdout[-3000:] + r.stderr[-2000:])
        hana = User.objects.get(username="e2e_hana")
        dodi = User.objects.get(username="e2e_dodi")
        self.assertEqual((hana.unit.head, dodi.supervisor, dodi.position), (hana, hana, "Koordinator Diklat"))
