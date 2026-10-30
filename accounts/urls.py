from django.urls import path

from . import views

app_name = "organisasi"
urlpatterns = [
    path("", views.index, name="index"),
    path("baru/", views.unit_create, name="create"),
    path("<int:pk>/", views.unit_edit, name="edit"),
    path("<int:pk>/nonaktifkan/", views.unit_deactivate, name="deactivate"),
    path("<int:pk>/aktifkan/", views.unit_activate, name="activate"),
    path("<int:pk>/hubungan/", views.relation_add, name="relation_add"),
    path("<int:pk>/hubungan/<int:rel_pk>/hapus/", views.relation_remove, name="relation_remove"),
]
