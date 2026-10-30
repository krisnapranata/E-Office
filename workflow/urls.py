from django.urls import path

from . import views

app_name = "workflow"
urlpatterns = [
    path("", views.task_list, name="list"),
    path("baru/", views.task_create, name="create"),
    path("<int:pk>/", views.task_detail, name="detail"),
    path("<int:pk>/terima/", views.task_accept, name="accept"),
    path("<int:pk>/progres/", views.task_progress, name="progress"),
    path("<int:pk>/bukti/", views.task_evidence, name="evidence"),
    path("<int:pk>/kirim/", views.task_submit, name="submit"),
    path("<int:pk>/verifikasi/", views.task_verify, name="verify"),
    path("<int:pk>/ubah-penugasan/", views.task_reassign, name="reassign"),
    path("<int:pk>/batal/", views.task_cancel, name="cancel"),
    path("<int:pk>/minta-pembaruan/", views.task_request_update, name="request_update"),
    path("<int:pk>/arahan/", views.task_direction, name="direction"),
    path("bukti/<int:pk>/unduh/", views.evidence_download, name="evidence_download"),
]
