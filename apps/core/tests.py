from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.core.models import BusinessUnit, Cliente, PerfilUsuario
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
