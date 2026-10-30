from django.urls import path

from . import views

app_name = "letters"
urlpatterns = [
    path("masuk/", views.incoming_list, name="incoming_list"),
    path("masuk/baru/", views.incoming_create, name="incoming_create"),
    path("masuk/<int:pk>/", views.incoming_detail, name="incoming_detail"),
    path("masuk/<int:pk>/disposisi/", views.disposition_create, name="disposition_create"),
    path("keluar/", views.outgoing_list, name="outgoing_list"),
    path("keluar/baru/", views.outgoing_create, name="outgoing_create"),
    path("lampiran/<str:kind>/<int:pk>/", views.attachment_download, name="attachment"),
    path("disposisi/", views.disposition_list, name="disposition_list"),
    path("disposisi/<int:pk>/", views.disposition_detail, name="disposition_detail"),
]
