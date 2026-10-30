from .models import PengaturanAplikasi


def mode_aplikasi(request):
    """Penanda MODE DEMO di bilah atas untuk pengguna yang login."""
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {}
    return {"mode_demo": PengaturanAplikasi.ambil().is_demo}
