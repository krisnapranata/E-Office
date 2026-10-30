from datetime import timedelta

from django.db.models import Count, F, Q
from django.utils import timezone

from instructions.models import Instruction, InstructionTarget
from instructions.services import visible_instructions
from letters.models import Disposition
from letters.services import visible_dispositions
from workflow.access import visible_tasks
from workflow.models import CLOSED_STATUSES, TaskStatus


def summary(user, today=None):
    """Seluruh angka dihitung dari lingkup data pengguna, sehingga konsisten dengan daftar detail."""
    today = today or timezone.localdate()
    tasks = visible_tasks(user)
    S = TaskStatus
    by_status = dict(tasks.values_list("status").annotate(n=Count("id", distinct=True)))
    instructions = visible_instructions(user)
    return {
        "today": today,
        "cards": [
            ("Belum dimulai", by_status.get(S.BELUM_DIMULAI, 0) + by_status.get(S.MENUNGGU_PENERIMAAN, 0),
             "flag=open&status=BELUM_DIMULAI", "secondary"),
            ("Berjalan", by_status.get(S.BERJALAN, 0), "status=BERJALAN", "primary"),
            ("Tenggat ≤ H-2", tasks.due_soon(today).count(), "flag=due_soon", "warning"),
            ("Terlambat", tasks.overdue(today).count(), "flag=overdue", "danger"),
            ("Terhambat", by_status.get(S.TERHAMBAT, 0), "status=TERHAMBAT", "danger"),
            ("Menunggu verifikasi", by_status.get(S.MENUNGGU_VERIFIKASI, 0),
             "status=MENUNGGU_VERIFIKASI", "info"),
            ("Perlu perbaikan", by_status.get(S.PERLU_PERBAIKAN, 0), "status=PERLU_PERBAIKAN",
             "warning"),
            ("Selesai", by_status.get(S.SELESAI, 0), "status=SELESAI", "success"),
        ],
        "active_instructions": instructions.filter(status=Instruction.Status.DITERBITKAN)
        .filter(tasks__status__in=[s for s in S.values if s not in CLOSED_STATUSES]).distinct().count(),
        "unread_instructions": InstructionTarget.objects.filter(
            instruction__in=instructions.filter(status=Instruction.Status.DITERBITKAN),
            read_at=None).values("instruction").distinct().count(),
        "pending_dispositions": visible_dispositions(user).exclude(
            status=Disposition.Status.SELESAI).count(),
        "units": unit_performance(tasks, today),
        **agenda_dan_tindak_lanjut(user, tasks, today),
        "trend": completion_trend(tasks, today),
        "blocked": tasks.filter(status=S.TERHAMBAT).select_related("pic", "unit")[:5],
        "overdue": tasks.overdue(today).select_related("pic", "unit").order_by("due_date")[:10],
    }


def unit_performance(tasks, today):
    rows = (
        tasks.values("unit_id", "unit__code", "unit__name")
        .annotate(
            total=Count("id", distinct=True),
            done=Count("id", filter=Q(status=TaskStatus.SELESAI), distinct=True),
            on_time=Count("id", filter=Q(status=TaskStatus.SELESAI, due_date__isnull=False,
                                         submitted_at__date__lte=F("due_date")), distinct=True),
            overdue=Count("id", filter=Q(due_date__lt=today) & ~Q(status__in=CLOSED_STATUSES),
                          distinct=True),
        )
        .order_by("unit__code")
    )
    result = []
    for r in rows:
        r["on_time_pct"] = round(100 * r["on_time"] / r["done"]) if r["done"] else None
        result.append(r)
    return result


def completion_trend(tasks, today, weeks=6):
    start = today - timedelta(days=today.weekday()) - timedelta(weeks=weeks - 1)
    result = []
    for i in range(weeks):
        wk = start + timedelta(weeks=i)
        n = tasks.filter(status=TaskStatus.SELESAI, closed_at__date__gte=wk,
                         closed_at__date__lt=wk + timedelta(days=7)).count()
        result.append({"week": wk, "done": n})
    peak = max((r["done"] for r in result), default=0) or 1
    for r in result:
        r["pct"] = round(100 * r["done"] / peak)
    return result


def agenda_dan_tindak_lanjut(user, tasks, today):
    from agenda.models import AgendaEvent
    from agenda.services import visible_events
    from workflow.models import TaskSource

    # agenda hari ini tetap tampil walau sudah selesai (mis. rapat yang notulennya disetujui); yang batal tidak
    acara = visible_events(user).exclude(status=AgendaEvent.Status.DIBATALKAN).select_related("organizer")
    tl = tasks.filter(source_type=TaskSource.KEPUTUSAN_RAPAT)
    return {
        "agenda_hari_ini": acara.filter(start__date=today).order_by("start")[:8],
        "agenda_mendatang": acara.filter(status=AgendaEvent.Status.TERJADWAL, start__date__gt=today, start__date__lte=today + timedelta(days=7))
        .order_by("start")[:6],
        "tl_terbuka": tl.open().count(),
        "tl_terlambat": tl.overdue(today).count(),
    }


def beranda(user, today=None):
    """Beranda bergaya 'kabar': hal yang menunggu TINDAKAN pengguna ini, masing-masing dengan satu tombol jelas.
    -> {"kabar": [...], "tugas_saya": [...], "jumlah_tugas_saya": n}"""
    from django.urls import reverse

    from instructions.models import InstructionTarget
    from letters.models import IncomingLetter
    from workflow.models import Task

    today = today or timezone.localdate()
    S = TaskStatus
    kabar = []

    def tambah(urut, ikon, warna, judul, teks, ket, url, tombol):
        kabar.append({"urut": urut, "ikon": ikon, "warna": warna, "judul": judul, "teks": teks, "ket": ket,
                      "url": url, "tombol": tombol})

    milik = Task.objects.filter(pic=user).select_related("unit", "created_by")
    for t in milik.filter(status=S.MENUNGGU_PENERIMAAN).order_by("due_date")[:10]:
        tambah(1, "bi-inbox", "primary", "Tugas baru untuk Anda", t.title,
               f"Dari {t.created_by} · tenggat {_tgl(t.due_date)}", reverse("workflow:detail", args=[t.pk]),
               "Lihat & terima")
    for t in milik.filter(status=S.PERLU_PERBAIKAN).order_by("due_date")[:10]:
        tambah(2, "bi-arrow-counterclockwise", "warning", "Hasil Anda perlu diperbaiki", t.title,
               f"Tenggat {_tgl(t.due_date)}", reverse("workflow:detail", args=[t.pk]), "Perbaiki")
    dekat = milik.filter(status__in=[S.BELUM_DIMULAI, S.BERJALAN, S.TERHAMBAT], due_date__lte=today + timedelta(days=2))
    for t in dekat.order_by("due_date")[:10]:
        telat = t.due_date < today
        tambah(3, "bi-alarm", "danger" if telat else "warning",
               "Tugas Anda terlambat" if telat else "Tenggat tugas sudah dekat", t.title,
               f"Tenggat {_tgl(t.due_date)} · progres {t.progress}%", reverse("workflow:detail", args=[t.pk]),
               "Laporkan progres")
    periksa = Task.objects.filter(verifier=user, status=S.MENUNGGU_VERIFIKASI).select_related("pic")
    for t in periksa.order_by("submitted_at")[:10]:
        tambah(1, "bi-clipboard-check", "info", "Hasil kerja menunggu Anda periksa", t.title,
               f"Dikirim oleh {t.pic}", reverse("workflow:detail", args=[t.pk]), "Periksa hasil")
    for d in (Disposition.objects.filter(to_user=user, status__in=[Disposition.Status.TERKIRIM, Disposition.Status.DIBACA])
              .select_related("letter", "from_user").order_by("-id")[:10]):
        tambah(2, "bi-signpost-split", "primary", "Disposisi surat untuk Anda", d.letter.subject,
               f"Dari {d.from_user}", reverse("letters:disposition_detail", args=[d.pk]), "Buka disposisi")
    for it in (InstructionTarget.objects.filter(pic=user, read_at=None, instruction__status=Instruction.Status.DITERBITKAN)
               .select_related("instruction", "instruction__created_by").order_by("-id")[:10]):
        i = it.instruction
        tambah(2, "bi-megaphone", "primary", "Instruksi baru untuk Anda", i.title, f"Dari {i.created_by}",
               reverse("instructions:detail", args=[i.pk]), "Baca instruksi")
    if user.role == "DIREKTUR":
        for s in IncomingLetter.objects.filter(dispositions__isnull=True).order_by("-received_date")[:10]:
            tambah(2, "bi-envelope-exclamation", "warning", "Surat masuk belum didisposisi", s.subject,
                   f"Dari {s.sender} · diterima {_tgl(s.received_date)}",
                   reverse("letters:incoming_detail", args=[s.pk]), "Disposisikan")
    kabar.sort(key=lambda k: k["urut"])

    aktif = milik.exclude(status__in=[*CLOSED_STATUSES, S.DRAF]).order_by(F("due_date").asc(nulls_last=True))
    return {"kabar": kabar, "tugas_saya": aktif[:6], "jumlah_tugas_saya": aktif.count()}


def _tgl(d):
    return d.strftime("%d-%m-%Y") if d else "–"
