def scope(request):
    return {
        "scope_es_admin": getattr(request, "scope_es_admin", False),
    }
