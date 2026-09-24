"""Reglas de scope: qué clientes y plantas puede ver un usuario."""

from .models import BusinessUnit, Cliente


def get_scope_for_user(user):
    """Devuelve (clientes, business_units, es_admin)."""
    if not user or not user.is_authenticated:
        return Cliente.objects.none(), BusinessUnit.objects.none(), False
    if user.is_superuser:
        return Cliente.objects.all(), BusinessUnit.objects.all(), True
    perfil = getattr(user, "perfil", None)
    if perfil and perfil.es_admin:
        return Cliente.objects.all(), BusinessUnit.objects.all(), True
    if perfil:
        return perfil.clientes.all(), perfil.business_units.all(), False
    return Cliente.objects.none(), BusinessUnit.objects.none(), False


def get_clientes_for_user(user):
    """Compatibilidad: devuelve (clientes, es_admin)."""
    clientes, _, es_admin = get_scope_for_user(user)
    return clientes, es_admin


def get_business_units_for_user(user):
    """Devuelve (business_units, es_admin)."""
    _, business_units, es_admin = get_scope_for_user(user)
    return business_units, es_admin


def user_can_see_cliente(user, cliente):
    clientes, es_admin = get_clientes_for_user(user)
    if es_admin:
        return True
    return clientes.filter(pk=cliente.pk).exists()


def user_can_see_business_unit(user, business_unit):
    business_units, es_admin = get_business_units_for_user(user)
    if es_admin:
        return True
    return business_units.filter(pk=business_unit.pk).exists()
