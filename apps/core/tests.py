from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.core.models import BusinessUnit, Cliente, GrupoCliente, PerfilUsuario
from apps.core.scoping import get_scope_for_user


class PerfilTests(TestCase):
    def setUp(self):
        self.bu = BusinessUnit.objects.create(code="set_tj2", nombre="TJ2")
        self.cliente = Cliente.objects.create(nombre="FLEX")
        self.user = User.objects.create_user("cliente", password="ClaveSegura123!")
        self.perfil = PerfilUsuario.objects.create(user=self.user)
        self.perfil.clientes.add(self.cliente)
        self.perfil.business_units.add(self.bu)
        self.perfil.debe_cambiar_password = False
        self.perfil.save()

    def test_scope_incluye_planta(self):
        clientes, business_units, es_admin = get_scope_for_user(self.user)
        self.assertIn(self.cliente, clientes)
        self.assertIn(self.bu, business_units)
        self.assertFalse(es_admin)

    def test_perfil_sincroniza_correo(self):
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("core:perfil"), {"correo": "cliente@example.com"}
        )
        self.assertEqual(resp.status_code, 302)
        self.user.refresh_from_db()
        self.perfil.refresh_from_db()
        self.assertEqual(self.user.email, "cliente@example.com")
        self.assertEqual(self.perfil.correos, ["cliente@example.com"])

    def test_cambio_password_obligatorio(self):
        self.perfil.debe_cambiar_password = True
        self.perfil.save()
        self.client.force_login(self.user)

        resp = self.client.get(reverse("metricas:index"))
        self.assertRedirects(
            resp, reverse("core:cambio_password"), fetch_redirect_response=False
        )

        resp = self.client.post(
            reverse("core:cambio_password"),
            {
                "old_password": "ClaveSegura123!",
                "new_password1": "NuevaClave456!",
                "new_password2": "NuevaClave456!",
            },
        )
        self.assertRedirects(
            resp, reverse("core:perfil"), fetch_redirect_response=False
        )
        self.perfil.refresh_from_db()
        self.assertFalse(self.perfil.debe_cambiar_password)


class GrupoClienteMultiUdnTests(TestCase):
    """Un mismo `group` puede existir en varias UDN sin reasignarse."""

    def test_mismo_group_en_dos_udn(self):
        bu_tj = BusinessUnit.objects.create(code="set_tj2", nombre="TJ")
        bu_cab = BusinessUnit.objects.create(code="set_cab", nombre="CAB")
        cliente = Cliente.objects.create(nombre="SCHNEIDER")
        g_tj = GrupoCliente.objects.create(
            group="SCN-SCHNEIDER", cliente=cliente, business_unit=bu_tj
        )
        g_cab = GrupoCliente.objects.create(
            group="SCN-SCHNEIDER", cliente=cliente, business_unit=bu_cab
        )
        self.assertNotEqual(g_tj.pk, g_cab.pk)
        self.assertEqual(
            GrupoCliente.objects.filter(group="SCN-SCHNEIDER").count(), 2
        )
        self.assertEqual(g_tj.business_unit, bu_tj)
        self.assertEqual(g_cab.business_unit, bu_cab)
