from django.urls import path

from . import views

app_name = "instructions"
urlpatterns = [
    path("", views.instruction_list, name="list"),
    path("baru/", views.instruction_create, name="create"),
    path("<int:pk>/", views.instruction_detail, name="detail"),
    path("<int:pk>/ubah/", views.instruction_edit, name="edit"),
    path("<int:pk>/penerima/", views.target_add, name="target_add"),
    path("<int:pk>/penerima/<int:target_pk>/hapus/", views.target_remove, name="target_remove"),
    path("<int:pk>/terbitkan/", views.instruction_issue, name="issue"),
    path("<int:pk>/batal/", views.instruction_cancel, name="cancel"),
    path("<int:pk>/lampiran/", views.attachment_download, name="attachment"),
]
