"""Pengaturan Aplikasi: Mode Demo / Reset data demo (khusus Administrator; di DB dev, semua di-rollback)."""
from accounts.models import Role, User
from pengaturan.models import PengaturanAplikasi
from pengaturan.services import FRASA_RESET
from testutils.factories import user
from workflow.models import Task

from . import skenario
from ._bantu import url


@skenario("pengaturan", "Pengaturan Aplikasi: tolak non-admin & akun demo → reset data demo → Mode Produksi → muat ulang demo",
          crud=True, role="staf_igd", lambat=True, menu=["pengaturan:index", "pengaturan:demo", "pengaturan:reset"])
def _(u):
    u.get(url("pengaturan:index"), harap=403)
    u.post(url("pengaturan:reset"), {"frasa": FRASA_RESET}, harap=403)
    u.w.admin = user(Role.ADMIN, unit=u.w.dir_unit, username="qa_admin")
    u.sebagai("admin")
    u.get(url("pengaturan:index"), ada=["Pengaturan Aplikasi", "Data demo saat ini", FRASA_RESET])
    u.post(url("pengaturan:reset"), {"frasa": "salah"}, harap=200, follow=True, ada=["untuk konfirmasi"])
    u.harap(User.objects.filter(username__startswith="demo_").exists(), "frasa salah tetap mereset")
    asli = Task.objects.exclude(created_by__username__startswith="demo_").exclude(
        created_by__username__in=["direktur", "sekretaris", "wadir", "ka_igd", "ka_farmasi", "staf_igd",
                                  "staf_farmasi", "arsip", "auditor"]).count()
    u.post(url("pengaturan:reset"), {"frasa": FRASA_RESET}, harap=200, follow=True, ada=["Mode Produksi aktif"])
    u.harap(not User.objects.filter(username__startswith="demo_").exists(), "akun demo tidak terhapus")
    u.harap(not PengaturanAplikasi.ambil().is_demo, "mode tidak berubah ke produksi")
    u.harap(Task.objects.count() == asli, f"tugas non-demo ikut terhapus ({Task.objects.count()} != {asli})")
    u.get(url("dashboard:home"), tidak_ada=["MODE DEMO"])
    u.post(url("pengaturan:demo"), harap=200, follow=True, ada=["Mode Demo aktif", "MODE DEMO"])
    u.harap(User.objects.filter(username="demo_dimas.aditya").exists(), "demo tidak dimuat ulang")
