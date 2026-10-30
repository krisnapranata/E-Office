from django.urls import path

from . import views

app_name = "laporan"
urlpatterns = [
    path("", views.index, name="index"),
    path("excel/", views.export_xlsx, name="xlsx"),
    path("arsipkan/", views.archive, name="archive"),
]
