"""Reglas de scope: qué clientes puede ver un usuario."""

from .models import Cliente


def get_clientes_for_user(user):
    """Devuelve (queryset_clientes, es_admin).

    Admin (superuser o perfil.es_admin) ve todo; si no, sólo sus clientes.
    """
    if not user or not user.is_authenticated:
        return Cliente.objects.none(), False
    if user.is_superuser:
        return Cliente.objects.all(), True
    perfil = getattr(user, "perfil", None)
    if perfil and perfil.es_admin:
        return Cliente.objects.all(), True
    if perfil:
        return perfil.clientes.all(), False
    return Cliente.objects.none(), False


def user_can_see_cliente(user, cliente):
    clientes, es_admin = get_clientes_for_user(user)
    if es_admin:
        return True
    return clientes.filter(pk=cliente.pk).exists()
