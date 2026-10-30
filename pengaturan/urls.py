from django.urls import path

from . import views

app_name = "pengaturan"
urlpatterns = [
    path("", views.index, name="index"),
    path("demo/", views.muat, name="demo"),
    path("reset/", views.reset, name="reset"),
    path("aturan-penugasan/", views.aturan_penugasan, name="aturan"),
]
