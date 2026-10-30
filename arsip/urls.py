from django.urls import path

from . import views

app_name = "arsip"
urlpatterns = [
    path("", views.archive_list, name="list"),
    path("baru/", views.archive_create, name="create"),
    path("<int:pk>/", views.archive_detail, name="detail"),
    path("<int:pk>/versi/", views.archive_version, name="version_add"),
    path("<int:pk>/metadata/", views.archive_metadata, name="metadata"),
    path("<int:pk>/usul-musnah/", views.archive_propose, name="propose"),
    path("<int:pk>/putuskan-musnah/", views.archive_decide, name="decide"),
    path("versi/<int:pk>/unduh/", views.version_download, name="download"),
]
