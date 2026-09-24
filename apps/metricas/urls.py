from django.urls import path

from . import views

app_name = "metricas"

urlpatterns = [
    path("", views.index, name="index"),
    path("cliente/", views.cliente, name="cliente"),
    path("cliente/enviar/", views.enviar_detalle, name="enviar_detalle"),
    path("cliente/retrasos/", views.retrasos, name="retrasos"),
]
