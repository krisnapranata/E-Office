"""E-Agenda: jadwal, undangan, perubahan, bahan, kalender, pembatalan, pengingat, hak akses."""
from datetime import timedelta

from django.utils import timezone

from agenda.models import AgendaEvent
from agenda.services import run_agenda_reminders
from notifications.models import Notification

from . import skenario
from ._bantu import JUDUL_QA, berkas, url


def _dt(hari, jam=9):
    d = timezone.localdate() + timedelta(days=hari)
    return f"{d.isoformat()}T{jam:02d}:00"


@skenario("agenda", "Agenda rapat: buat → undangan → ubah jadwal → bahan → kalender → batal beralasan", crud=True,
          role="sekretaris", menu=["agenda:list", "agenda:calendar", "agenda:create", "agenda:detail", "agenda:edit",
                                   "agenda:cancel", "agenda:material_add", "agenda:material_download"])
def _(u):
    w = u.w
    judul = f"{JUDUL_QA} Rapat koordinasi pelayanan"
    u.get(url("agenda:create"), ada=["Agenda baru"])
    u.post(url("agenda:create"), {"title": judul, "kind": "RAPAT", "start": _dt(2), "end": _dt(2, 8),
                                  "location": "Ruang rapat", "organizer": w.direktur.pk,
                                  "participants": [w.wadir.pk, w.ka_igd.pk], "classification": "BIASA"},
           harap=200, follow=True, ada=["Waktu selesai harus setelah waktu mulai"])
    u.post(url("agenda:create"), {"title": judul, "kind": "RAPAT", "start": _dt(2), "end": _dt(2, 11),
                                  "location": "Ruang rapat", "organizer": w.direktur.pk,
                                  "participants": [w.wadir.pk, w.ka_igd.pk], "classification": "BIASA"}, harap=302)
    ev = AgendaEvent.objects.get(title=judul)
    for p in (w.wadir, w.ka_igd, w.direktur):
        u.harap(Notification.objects.filter(recipient=p, kind="agenda.invite").exists(), f"undangan ke {p} tidak ada")
    u.post(url("agenda:edit", ev.pk), {"title": judul, "kind": "RAPAT", "start": _dt(3, 13), "end": _dt(3, 15),
                                       "location": "Aula", "organizer": w.direktur.pk,
                                       "participants": [w.wadir.pk, w.ka_igd.pk, w.ka_farmasi.pk],
                                       "classification": "BIASA"}, harap=302)
    u.harap(Notification.objects.filter(recipient=w.wadir, kind="agenda.reschedule").exists(),
            "peserta lama tidak diberi tahu perubahan jadwal")
    u.harap(Notification.objects.filter(recipient=w.ka_farmasi, kind="agenda.invite").exists(),
            "peserta baru tidak diundang")
    u.sebagai("ka_igd")
    u.get(url("agenda:list"), ada=[judul])
    u.post(url("agenda:material_add", ev.pk), {"file": berkas("bahan.pdf"), "description": "Data IGD"}, harap=302)
    m = ev.materials.get()
    u.get(url("agenda:material_download", m.pk), harap=200)
    u.get(url("agenda:edit", ev.pk), harap=403)                  # peserta tidak boleh mengubah
    bulan = (timezone.localdate() + timedelta(days=3)).strftime("%Y-%m")
    u.get(url("agenda:calendar") + f"?bulan={bulan}", ada=[judul[:20]])
    u.sebagai("staf_farmasi")                                     # tidak diundang
    u.get(url("agenda:detail", ev.pk), harap=404)
    u.get(url("agenda:material_download", m.pk), harap=404)
    u.sebagai("sekretaris")
    u.post(url("agenda:cancel", ev.pk), {"reason": ""}, harap=200, follow=True, ada=["Alasan pembatalan wajib"])
    u.post(url("agenda:cancel", ev.pk), {"reason": "Direktur dinas luar"}, harap=302)
    ev.refresh_from_db()
    u.harap(ev.status == AgendaEvent.Status.DIBATALKAN, f"status {ev.status}")
    u.harap(Notification.objects.filter(recipient=w.ka_igd, kind="agenda.cancel").exists(), "pembatalan tidak dikabarkan")


@skenario("agenda", "Pengingat agenda H-1 & hari-H: terkirim sekali ke penyelenggara & peserta; kegiatan selesai",
          role="ka_igd", menu=["agenda:complete"])
def _(u):
    w = u.w
    besok = timezone.now() + timedelta(days=1)
    from agenda.services import create_event

    ev = create_event(w.ka_igd, participants=[w.staf_igd], title=f"{JUDUL_QA} Apel pagi", kind="KEGIATAN",
                      start=besok, location="Halaman IGD")
    for _ in range(3):
        run_agenda_reminders(timezone.localdate())
    n = Notification.objects.filter(kind="agenda.reminder", title__contains="Apel pagi")
    u.harap(n.filter(recipient=w.staf_igd).count() == 1 and n.filter(recipient=w.ka_igd).count() == 1,
            f"pengingat: {list(n.values_list('recipient__username', flat=True))}")
    u.post(url("agenda:complete", ev.pk), harap=302)
    ev.refresh_from_db()
    u.harap(ev.status == AgendaEvent.Status.SELESAI, f"status {ev.status}")
    run_agenda_reminders(timezone.localdate())
    u.harap(n.count() == 2, "agenda selesai masih diingatkan")
