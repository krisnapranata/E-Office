"""E-Instruksi: skenario E2E PRD 18.4 C no. 1 (instruksi sampai penutupan) + draf/batal."""
from instructions.models import Instruction
from workflow.models import Task, TaskStatus

from . import skenario
from ._bantu import JUDUL_QA, berkas, hari, kartu_dashboard, url


def _buat(u, judul, **lain):
    data = {"title": judul, "description": "Lakukan audit sesuai SOP.", "instruction_date": hari(),
            "priority": "TINGGI", "classification": "BIASA", "due_date": hari(3),
            "completion_criteria": "Laporan audit + foto rak", "requires_evidence": "on",
            "requires_verification": "on", "on_behalf_of": ""}
    data.update(lain)
    u.get(url("instructions:create"), ada=["Instruksi baru"])
    u.post(url("instructions:create"), data, harap=302)
    return Instruction.objects.get(title=judul)


@skenario("instruksi", "Instruksi → PIC terima, progres, bukti, kirim → verifikasi → dashboard", crud=True,
          menu=["instructions:list", "instructions:create", "instructions:detail", "instructions:target_add",
                "instructions:issue", "workflow:list", "workflow:detail", "workflow:accept", "workflow:progress",
                "workflow:evidence", "workflow:submit", "workflow:verify", "workflow:evidence_download"])
def _(u):
    w = u.w
    judul = f"{JUDUL_QA} Audit stok obat high alert"
    sebelum = {lbl: n for lbl, n, _ in kartu_dashboard(u.teks(u.get("/")))}
    ins = _buat(u, judul)
    det = url("instructions:detail", ins.pk)
    u.get(det, ada=[ins.code, "Belum ada penerima"])
    u.post(url("instructions:target_add", ins.pk), {"unit": w.farmasi.pk, "pic": w.staf_farmasi.pk}, harap=302)
    u.post(url("instructions:issue", ins.pk), harap=302)
    ins.refresh_from_db()
    u.harap(ins.status == Instruction.Status.DITERBITKAN, f"instruksi tidak terbit: {ins.status}")
    task = Task.objects.get(instruction=ins)
    u.harap(task.verifier_id == w.direktur.pk and task.source_type == "INSTRUKSI", "tautan tugas ↔ instruksi salah")
    u.get(url("instructions:list"), ada=[ins.code])

    u.sebagai("staf_farmasi")
    u.get(url("workflow:list"), ada=[judul])
    u.harap(ins.targets.get().read_at is None, "instruksi tercatat dibaca sebelum dibuka")
    td = url("workflow:detail", task.pk)
    u.get(td, ada=["Terima tugas"])          # PIC membuka tugasnya -> instruksi sumber tercatat dibaca
    u.harap(ins.targets.get().read_at is not None, "status dibaca penerima tidak tercatat")
    u.get(det, ada=[ins.code])
    u.post(url("workflow:accept", task.pk), harap=302)
    u.post(url("workflow:progress", task.pk), {"progress": 60, "status": "BERJALAN", "note": "Rak A selesai"},
           harap=302)
    u.post(url("workflow:evidence", task.pk), {"file": berkas(), "description": "foto rak"}, harap=302)
    ev = task.evidences.get()
    u.get(url("workflow:evidence_download", ev.pk), harap=200)
    u.post(url("workflow:submit", task.pk), {"note": "Audit selesai"}, harap=302)
    task.refresh_from_db()
    u.harap(task.status == TaskStatus.MENUNGGU_VERIFIKASI, f"status setelah kirim: {task.status}")

    u.sebagai("direktur")
    u.get(td, ada=["Verifikasi hasil"])
    u.post(url("workflow:verify", task.pk), {"decision": "approve", "note": "Sesuai"}, harap=302)
    task.refresh_from_db()
    u.harap(task.status == TaskStatus.SELESAI and task.closed_at, f"tugas tidak tertutup: {task.status}")
    sesudah = {lbl: n for lbl, n, _ in kartu_dashboard(u.teks(u.get("/")))}
    u.harap(sesudah.get("Selesai", 0) == sebelum.get("Selesai", 0) + 1,
            f"dashboard Selesai {sebelum.get('Selesai')} -> {sesudah.get('Selesai')} (harap +1)")


@skenario("instruksi", "Instruksi draf: ubah, lampiran, tambah/hapus penerima, terbit, batal beralasan", crud=True,
          menu=["instructions:edit", "instructions:target_remove", "instructions:cancel", "instructions:attachment"],
          role="sekretaris")
def _(u):
    w = u.w
    judul = f"{JUDUL_QA} Rapat koordinasi mutu"
    ins = _buat(u, judul, on_behalf_of=w.direktur.pk, attachment=berkas("undangan.pdf"))
    u.harap(ins.on_behalf_of_id == w.direktur.pk and ins.attachment, "atas nama / lampiran tidak tersimpan")
    u.get(url("instructions:attachment", ins.pk), harap=200)
    u.get(url("instructions:edit", ins.pk), ada=["Ubah"])
    u.post(url("instructions:edit", ins.pk), {
        "title": judul + " (revisi)", "description": "Revisi uraian", "instruction_date": hari(),
        "priority": "SEDANG", "classification": "BIASA", "due_date": hari(5), "completion_criteria": "Notulen",
        "requires_evidence": "on", "on_behalf_of": w.direktur.pk}, harap=302)
    ins.refresh_from_db()
    u.harap(ins.title.endswith("(revisi)") and not ins.requires_verification, "perubahan draf tidak tersimpan")
    u.post(url("instructions:target_add", ins.pk), {"unit": w.igd.pk, "pic": w.ka_igd.pk}, harap=302)
    u.post(url("instructions:target_add", ins.pk), {"unit": w.farmasi.pk, "pic": w.ka_farmasi.pk}, harap=302)
    t_farm = ins.targets.get(pic=w.ka_farmasi)
    u.post(url("instructions:target_remove", ins.pk, t_farm.pk), harap=302)
    u.harap(ins.targets.count() == 1, "penerima tidak terhapus")
    u.post(url("instructions:issue", ins.pk), harap=302)
    u.harap(ins.tasks.get().verifier_id == w.direktur.pk, "verifikator bukan pihak 'atas nama'")
    # setelah terbit, draf tidak bisa diubah lagi
    u.get(url("instructions:edit", ins.pk), harap=403)
    r = u.post(url("instructions:cancel", ins.pk), {"reason": ""}, harap=200, follow=True,
               ada=["Alasan pembatalan wajib diisi"])
    u.post(url("instructions:cancel", ins.pk), {"reason": "Jadwal berubah"}, harap=302)
    ins.refresh_from_db()
    u.harap(ins.status == Instruction.Status.DIBATALKAN, "instruksi tidak batal")
    u.harap(ins.tasks.get().status == TaskStatus.DIBATALKAN, "tugas terbuka tidak ikut batal")
    del r
