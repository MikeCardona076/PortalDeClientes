def scope(request):
    return {
        "scope_es_admin": getattr(request, "scope_es_admin", False),
        "scope_business_units": getattr(request, "scope_business_units", None),
    }
