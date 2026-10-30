"""Factory data sintetis untuk pengujian (tanpa data pasien/pribadi nyata)."""
import itertools
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from accounts.models import OrganizationUnit, Role, User
from workflow import services as workflow
from workflow.models import TaskSource

_seq = itertools.count(1)


def unit(code=None, parent=None, head=None):
    n = next(_seq)
    return OrganizationUnit.objects.create(code=code or f"U{n}", name=f"Unit {n}", parent=parent,
                                           head=head)


def user(role=Role.STAF, unit=None, supervisor=None, username=None):
    n = next(_seq)
    return User.objects.create_user(username=username or f"user{n}", password="pass-12345",
                                    role=role, unit=unit, supervisor=supervisor,
                                    first_name=f"User{n}")


def dummy_file(name="bukti.pdf", content=b"%PDF-1.4 dummy"):
    return SimpleUploadedFile(name, content, content_type="application/pdf")


def today():
    return timezone.localdate()


def direct_task(creator, pic, due=None, **kw):
    kw.setdefault("title", "Tugas uji")
    kw.setdefault("source_note", "Penugasan uji")
    return workflow.create_task(
        created_by=creator, source_type=TaskSource.LANGSUNG, unit=kw.pop("unit", pic.unit),
        pic=pic, due_date=due if due is not None else today() + timedelta(days=7), **kw)


class World:
    """Struktur organisasi minimal: Direksi > Yanmed > IGD, dan Farmasi terpisah."""

    def __init__(self):
        self.dir_unit = unit("DIR")
        self.yanmed = unit("YANMED", parent=self.dir_unit)
        self.igd = unit("IGD", parent=self.yanmed)
        self.farmasi = unit("FARM", parent=self.dir_unit)
        self.direktur = user(Role.DIREKTUR, self.dir_unit, username="direktur")
        self.sekretaris = user(Role.SEKRETARIS, self.dir_unit, self.direktur, "sekretaris")
        self.wadir = user(Role.WADIR, self.yanmed, self.direktur, "wadir")
        self.ka_igd = user(Role.KEPALA_UNIT, self.igd, self.wadir, "ka_igd")
        self.staf_igd = user(Role.STAF, self.igd, self.ka_igd, "staf_igd")
        self.ka_farmasi = user(Role.KEPALA_UNIT, self.farmasi, self.direktur, "ka_farmasi")
        self.staf_farmasi = user(Role.STAF, self.farmasi, self.ka_farmasi, "staf_farmasi")
        self.auditor = user(Role.AUDITOR, self.dir_unit, username="auditor")
        self.igd.head = self.ka_igd
        self.igd.save()


