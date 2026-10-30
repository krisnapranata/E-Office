from django.urls import path

from . import views_pengguna as views

app_name = "pengguna"
urlpatterns = [
    path("", views.index, name="index"),
    path("baru/", views.create, name="create"),
    path("<int:pk>/", views.edit, name="edit"),
    path("<int:pk>/nonaktifkan/", views.deactivate, name="deactivate"),
    path("<int:pk>/aktifkan/", views.activate, name="activate"),
]
