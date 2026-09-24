from datetime import date, time

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.models import (
    BusinessUnit,
    Cliente,
    GrupoCliente,
    PerfilUsuario,
    Semana,
    ServicioRutaSemana,
)
from apps.metricas.views import _correos_cliente


class RetrasosViewTests(TestCase):
    def setUp(self):
        self.bu = BusinessUnit.objects.create(code="set_tj2", nombre="TJ2")
        self.cliente = Cliente.objects.create(nombre="FLEX")
        self.grupo = GrupoCliente.objects.create(
            group="FLEX-GRAL", cliente=self.cliente, business_unit=self.bu
        )
        self.semana = Semana.objects.create(
            year=2026, week=34, inicio=date(2026, 8, 17), fin=date(2026, 8, 23)
        )
        self.admin = User.objects.create_superuser("admin", password="x")
        self.user = User.objects.create_user("normal", password="x")

        ServicioRutaSemana.objects.create(
            business_unit=self.bu,
            grupo=self.grupo,
            semana=self.semana,
            external_id="1",
            ruta_seq="0010",
            fecha_inicio=date(2026, 8, 17),
            fecha_fin=date(2026, 8, 17),
            prog_fin=time(11, 0),
            real_fin=time(11, 20),
            dif_fin=20,
            diagnostico_inicio="Retrasado",
        )

    def test_admin_ve_retrasos(self):
        self.client.force_login(self.admin)
        resp = self.client.get(
            reverse("metricas:retrasos"),
            {
                "cliente": "FLEX",
                "udn": "set_tj2",
                "anio": 2026,
                "semana": 34,
                "ruta": "0010",
                "grupo": self.grupo.id,
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["rows"][0]["id"], "1")
        self.assertEqual(data["rows"][0]["dif_fin"], 20)

    def test_usuario_sin_cliente_no_ve_retrasos(self):
        self.client.force_login(self.user)
        resp = self.client.get(
            reverse("metricas:retrasos"),
            {"cliente": "FLEX", "udn": "set_tj2", "anio": 2026, "semana": 34},
        )
        self.assertEqual(resp.status_code, 403)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_admin_envia_correo_detalle(self):
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("metricas:enviar_detalle"),
            {
                "cliente": "FLEX",
                "udn": "set_tj2",
                "anio": 2026,
                "semana": 34,
                "window": "14d",
                "destinatarios": "a@example.com, b@example.com",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("a@example.com", mail.outbox[0].to)
        self.assertIn("b@example.com", mail.outbox[0].to)
        html = mail.outbox[0].alternatives[0][0]
        self.assertIn("FLEX", html)
        self.assertIn("Detalle de retrasos", html)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_correo_invalido_no_envia(self):
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("metricas:enviar_detalle"),
            {
                "cliente": "FLEX",
                "udn": "set_tj2",
                "anio": 2026,
                "semana": 34,
                "window": "14d",
                "destinatarios": "no-es-correo",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)

    def test_admin_ve_boton_correo(self):
        self.client.force_login(self.admin)
        resp = self.client.get(
            reverse("metricas:cliente"),
            {"cliente": "FLEX", "udn": "set_tj2", "anio": 2026, "semana": 34, "window": "14d"},
        )
        self.assertContains(resp, "ENVIAR CORREO CON DETALLE")

    def test_usuario_no_admin_no_envia(self):
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("metricas:enviar_detalle"),
            {
                "cliente": "FLEX",
                "udn": "set_tj2",
                "anio": 2026,
                "semana": 34,
                "window": "14d",
                "destinatarios": "a@example.com",
            },
        )
        self.assertEqual(resp.status_code, 403)

    def test_destinatarios_incluye_superuser(self):
        User.objects.create_superuser("jefa", email="jefa@example.com", password="x")
        self.assertIn("jefa@example.com", _correos_cliente(self.cliente, self.bu))

    def test_destinatarios_excluye_remitente(self):
        User.objects.create_superuser("jefa", email="jefa@example.com", password="x")
        correos = _correos_cliente(
            self.cliente, self.bu, excluir="jefa@example.com"
        )
        self.assertNotIn("jefa@example.com", correos)

    def test_destinatarios_cliente_y_planta(self):
        usuario = User.objects.create_user("cliente2", password="x")
        perfil = PerfilUsuario.objects.create(
            user=usuario, correos=["contacto@example.com"]
        )
        perfil.clientes.add(self.cliente)
        perfil.business_units.add(self.bu)
        self.assertIn("contacto@example.com", _correos_cliente(self.cliente, self.bu))

    def test_destinatarios_sin_planta_no_aparece(self):
        usuario = User.objects.create_user("cliente3", password="x")
        perfil = PerfilUsuario.objects.create(
            user=usuario, correos=["sinplanta@example.com"]
        )
        perfil.clientes.add(self.cliente)
        self.assertNotIn(
            "sinplanta@example.com", _correos_cliente(self.cliente, self.bu)
        )
