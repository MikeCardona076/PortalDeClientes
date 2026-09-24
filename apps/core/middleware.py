from django.shortcuts import redirect
from django.urls import reverse

from .scoping import get_scope_for_user


class ScopeMiddleware:
    """Adjunta a cada request el scope de clientes y plantas del usuario."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        clientes, business_units, es_admin = get_scope_for_user(
            getattr(request, "user", None)
        )
        request.scope_clientes = clientes
        request.scope_business_units = business_units
        request.scope_es_admin = es_admin
        return self.get_response(request)


class CambioPasswordObligatorioMiddleware:
    """Fuerza a cambiar la contraseña en el primer ingreso."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            perfil = getattr(user, "perfil", None)
            if perfil and perfil.debe_cambiar_password:
                ruta = request.path
                permitidas = (
                    reverse("core:cambio_password"),
                    reverse("logout"),
                    "/admin/",
                    "/static/",
                    "/media/",
                )
                if not ruta.startswith(permitidas):
                    return redirect("core:cambio_password")
        return self.get_response(request)
