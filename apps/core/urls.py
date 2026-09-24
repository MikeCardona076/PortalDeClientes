from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.perfil, name="perfil"),
    path("password/", views.CambioPasswordView.as_view(), name="cambio_password"),
]
