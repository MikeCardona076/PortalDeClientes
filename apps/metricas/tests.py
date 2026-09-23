from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.core.models import (
    BusinessUnit,
    Cliente,
    GrupoCliente,
    Semana,
    ServicioRutaSemana,
)


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
