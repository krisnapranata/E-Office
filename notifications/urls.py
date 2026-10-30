from django.urls import path

from . import views

app_name = "notifications"
urlpatterns = [
    path("", views.notification_list, name="list"),
    path("badge/", views.badge, name="badge"),
    path("baca-semua/", views.mark_all_read, name="mark_all_read"),
    path("<int:pk>/buka/", views.open_notification, name="open"),
]
