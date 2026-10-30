"""Notifikasi internal: daftar, lencana HTMX, buka (tandai dibaca + arahkan), tandai semua dibaca."""
from workflow import services as alur

from . import skenario
from ._bantu import JUDUL_QA, url


@skenario("notifikasi", "Daftar, lencana, buka → dibaca & diarahkan, tandai semua dibaca", crud=True, role="staf_igd",
          menu=["notifications:list", "notifications:badge", "notifications:open", "notifications:mark_all_read"])
def _(u):
    w = u.w
    for i in range(2):
        alur.create_task(created_by=w.ka_igd, source_type="LANGSUNG", source_note="QA",
                         title=f"{JUDUL_QA} Notif {i}", unit=w.igd, pic=w.staf_igd, due_date=None)
    u.get(url("notifications:badge"), ada=["2"])
    n = w.staf_igd.notifications.filter(read_at=None).first()
    r = u.post(url("notifications:open", n.pk), harap=302)
    u.harap(r["Location"] == n.url, f"diarahkan ke {r['Location']} (harap {n.url})")
    n.refresh_from_db()
    u.harap(n.read_at is not None, "notifikasi tidak ditandai dibaca")
    u.post(url("notifications:mark_all_read"), harap=302)
    u.harap(not w.staf_igd.notifications.filter(read_at=None).exists(), "masih ada yang belum dibaca")
    u.get(url("notifications:badge"), tidak_ada=["badge"])
    u.sebagai("staf_farmasi")
    u.post(url("notifications:open", n.pk), harap=404)        # notifikasi milik orang lain
