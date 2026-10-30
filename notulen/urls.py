from django.urls import path

from . import views

app_name = "notulen"
urlpatterns = [
    path("", views.minutes_list, name="list"),
    path("rapat/<int:event_pk>/baru/", views.minutes_create, name="create"),
    path("<int:pk>/", views.minutes_detail, name="detail"),
    path("<int:pk>/ubah/", views.minutes_edit, name="edit"),
    path("<int:pk>/cetak/", views.minutes_print, name="print"),
    path("<int:pk>/lampiran/", views.minutes_attachment, name="attachment"),
    path("<int:pk>/keputusan/", views.decision_add, name="decision_add"),
    path("<int:pk>/keputusan/<int:decision_pk>/hapus/", views.decision_remove, name="decision_remove"),
    path("<int:pk>/keputusan/<int:decision_pk>/pic/", views.assignee_add, name="assignee_add"),
    path("<int:pk>/pic/<int:assignee_pk>/hapus/", views.assignee_remove, name="assignee_remove"),
    path("<int:pk>/ajukan/", views.minutes_submit, name="submit"),
    path("<int:pk>/kembalikan/", views.minutes_return, name="return"),
    path("<int:pk>/setujui/", views.minutes_approve, name="approve"),
]
