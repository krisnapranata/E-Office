"""Menu sidebar per peran: setiap orang hanya melihat menu yang ia pakai sehari-hari.

Ini soal TAMPILAN saja; hak akses tetap diperiksa di setiap view (halaman yang disembunyikan tetap bisa dibuka
lewat tautan bila perannya berhak, dan tetap ditolak bila tidak).
"""
from accounts.models import Role

R = Role
ATURAN = {
    "disposisi": {R.DIREKTUR, R.WADIR, R.KEPALA_UNIT, R.SEKRETARIS, R.AUDITOR},
    "surat": {R.DIREKTUR, R.WADIR, R.SEKRETARIS, R.ARSIP, R.AUDITOR, R.ADMIN},
    "rapat": {R.DIREKTUR, R.WADIR, R.KEPALA_UNIT, R.SEKRETARIS, R.AUDITOR, R.ADMIN},
    "laporan": {R.DIREKTUR, R.WADIR, R.KEPALA_UNIT, R.SEKRETARIS, R.ARSIP, R.AUDITOR, R.ADMIN},
    "organisasi": {R.DIREKTUR, R.WADIR, R.AUDITOR, R.ADMIN},
    "admin": {R.ADMIN},
}


def menu(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    if user.is_superuser:
        return {"menu": {k: True for k in ATURAN}}
    lihat = {k: user.role in peran for k, peran in ATURAN.items()}
    if not lihat["disposisi"]:                 # staf yang pernah menerima disposisi tetap melihat menunya
        from letters.models import Disposition
        lihat["disposisi"] = Disposition.objects.filter(to_user=user).exists()
    return {"menu": lihat}
