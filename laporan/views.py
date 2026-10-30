from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from accounts.permissions import Classification

from . import services
from .forms import ReportForm

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _laporan(request, data):
    form = ReportForm.default(data)
    rep = services.build(request.user, **{k: form.cleaned_data[k] for k in form.fields}) if form.is_valid() else None
    return form, rep


@login_required
def index(request):
    form, rep = _laporan(request, request.GET)
    params = request.GET.copy()
    return render(request, "laporan/index.html" if not request.GET.get("cetak") else "laporan/cetak.html",
                  {"form": form, "rep": rep, "querystring": params.urlencode()})


@login_required
def export_xlsx(request):
    form, rep = _laporan(request, request.GET)
    if not rep:
        messages.error(request, "Parameter laporan tidak valid.")
        return redirect("laporan:index")
    r = HttpResponse(services.xlsx(rep), content_type=XLSX)
    r["Content-Disposition"] = f'attachment; filename="laporan-eoffice-{rep["dibuat"]:%Y%m%d-%H%M}.xlsx"'
    return r


@login_required
@require_POST
def archive(request):
    from arsip.models import ArchiveDocument
    from arsip.services import retention_date
    from arsip.models import ArchiveVersion
    from audit import services as audit

    form, rep = _laporan(request, request.POST)
    if not rep:
        messages.error(request, "Parameter laporan tidak valid.")
        return redirect("laporan:index")
    hari = rep["dibuat"].date()
    doc = ArchiveDocument.objects.create(
        doc_type=ArchiveDocument.DocType.LAPORAN, number=f"LAP-{rep['dibuat']:%Y%m%d%H%M%S}", doc_date=hari,
        title=f"Laporan pelaksanaan {rep['parameter']['Periode']}", owner=request.user, unit=request.user.unit,
        classification=Classification.TERBATAS, keywords=" · ".join(f"{k}: {v}" for k, v in rep["parameter"].items())[:255],
        retention_until=retention_date(ArchiveDocument.DocType.LAPORAN, hari))
    v = ArchiveVersion(document=doc, version=1, original_name=f"{doc.number}.xlsx", uploaded_by=request.user,
                       note="Dibangkitkan dari E-Reporting")
    v.file.save(f"{doc.number}.xlsx", ContentFile(services.xlsx(rep)), save=False)
    v.save()
    audit.log(request.user, "report.archive", doc)
    messages.success(request, f"Laporan disimpan ke E-Arsip ({doc.number}).")
    return redirect("arsip:detail", doc.pk)
