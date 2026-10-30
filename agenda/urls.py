from django.urls import path

from . import views

app_name = "agenda"
urlpatterns = [
    path("", views.event_list, name="list"),
    path("kalender/", views.event_calendar, name="calendar"),
    path("baru/", views.event_create, name="create"),
    path("<int:pk>/", views.event_detail, name="detail"),
    path("<int:pk>/ubah/", views.event_edit, name="edit"),
    path("<int:pk>/batal/", views.event_cancel, name="cancel"),
    path("<int:pk>/selesai/", views.event_complete, name="complete"),
    path("<int:pk>/bahan/", views.material_add, name="material_add"),
    path("bahan/<int:pk>/unduh/", views.material_download, name="material_download"),
]
