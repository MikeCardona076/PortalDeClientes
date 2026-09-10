from .scoping import get_clientes_for_user


class ScopeMiddleware:
    """Adjunta a cada request el scope de clientes del usuario."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        clientes, es_admin = get_clientes_for_user(getattr(request, "user", None))
        request.scope_clientes = clientes
        request.scope_es_admin = es_admin
        return self.get_response(request)
