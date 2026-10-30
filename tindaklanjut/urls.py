from django.urls import path

from . import views

app_name = "tindaklanjut"
urlpatterns = [
    path("", views.index, name="index"),
    path("rapat/<int:event_pk>/", views.per_meeting, name="meeting"),
]
