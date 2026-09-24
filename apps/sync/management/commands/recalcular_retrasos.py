"""Recalcula retrasos/NS desde ServicioRutaSemana sin llamar a la API.

Uso: python manage.py recalcular_retrasos 2026 [--bunit set_tj2]
"""

from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.bustrax import ns
from apps.bustrax.weeks import prev_week
from apps.core.models import (
    RutaIndicadoresSemana,
    Semana,
    ServicioRutaSemana,
    ViajeSemana,
)
from apps.sync.services import _agregar_indicadores


class Command(BaseCommand):
    help = "Recalcula es_retraso, diagnóstico, indicadores por ruta y ViajeSemana."

    def add_arguments(self, parser):
        parser.add_argument("year", type=int)
        parser.add_argument("--bunit", action="append", dest="bunits", default=None)

    def handle(self, *args, **options):
        year = options["year"]
        bunits = options["bunits"]
        servicios = ServicioRutaSemana.objects.filter(semana__year=year).select_related(
            "grupo"
        )
        if bunits:
            servicios = servicios.filter(business_unit__code__in=bunits)

        actualizados = self._recalcular_servicios(servicios)
        rutas, viajes = self._recalcular_agregados(year, bunits)
        self.stdout.write(
            self.style.SUCCESS(
                f"Servicios {actualizados} · rutas {rutas} · viajes {viajes}"
            )
        )

    @transaction.atomic
    def _recalcular_servicios(self, servicios):
        lote = []
        total = 0
        for s in servicios.iterator():
            cancelado = (s.estado_viaje == "Cancelado") or (s.status == "9")
            retraso = (
                s.es_entrada
                and s.record_quality == "1"
                and s.dif_fin is not None
                and ns.RETRASO_MIN <= s.dif_fin < ns.RETRASO_MAX
            )
            if s.dif_ini is None:
                diag_ini = ""
            elif ns.RETRASO_MIN <= s.dif_ini < ns.RETRASO_MAX:
                diag_ini = "Retrasado"
            else:
                diag_ini = "A tiempo"
            s.es_retraso = bool(retraso)
            s.diagnostico_inicio = diag_ini
            lote.append(s)
            total += 1
            if len(lote) >= 1000:
                ServicioRutaSemana.objects.bulk_update(
                    lote, ["es_retraso", "diagnostico_inicio"]
                )
                lote = []
        if lote:
            ServicioRutaSemana.objects.bulk_update(
                lote, ["es_retraso", "diagnostico_inicio"]
            )
        return total

    @transaction.atomic
    def _recalcular_agregados(self, year, bunits):
        servicios = ServicioRutaSemana.objects.filter(semana__year=year).select_related(
            "grupo"
        )
        if bunits:
            servicios = servicios.filter(business_unit__code__in=bunits)

        viajes = defaultdict(lambda: {"total": 0, "entradas": 0, "retrasos": 0})
        for s in servicios.iterator():
            cancelado = (s.estado_viaje == "Cancelado") or (s.status == "9")
            completado = s.status in ("5", "6", "7", "8") and not cancelado
            kv = (s.grupo.cliente_id, s.semana_id)
            v = viajes[kv]
            v["total"] += 1 if completado else 0
            v["entradas"] += 1 if s.es_entrada else 0
            v["retrasos"] += 1 if s.es_retraso else 0

        RutaIndicadoresSemana.objects.filter(semana__year=year).delete()
        total_rutas = 0
        for semana in Semana.objects.filter(year=year):
            pyear, pweek = prev_week(semana.year, semana.week)
            previa = Semana.objects.filter(year=pyear, week=pweek).first()
            for mode, lista in (
                ("7d", [semana]),
                ("14d", [semana] + ([previa] if previa else [])),
            ):
                qs = ServicioRutaSemana.objects.filter(semana__in=lista).select_related(
                    "grupo"
                )
                if bunits:
                    qs = qs.filter(business_unit__code__in=bunits)
                for (grupo_id, ruta), data in _agregar_indicadores(qs).items():
                    RutaIndicadoresSemana.objects.create(
                        business_unit_id=data["business_unit_id"],
                        semana_id=semana.id,
                        grupo_id=grupo_id,
                        ruta_seq=ruta,
                        window_mode=mode,
                        descripcion=data["descripcion"],
                        servicios=data["servicios"],
                        entradas=data["entradas"],
                        retrasos=data["retrasos"],
                        ns=data["ns"],
                        source="api",
                    )
                    total_rutas += 1

        # Reemplaza ViajeSemana del año.
        ViajeSemana.objects.filter(semana__year=year).delete()
        for (cliente_id, semana_id), data in viajes.items():
            entradas = data["entradas"]
            ViajeSemana.objects.create(
                cliente_id=cliente_id,
                semana_id=semana_id,
                total=data["total"],
                entradas=entradas,
                retrasos=data["retrasos"],
                ns=round((entradas - data["retrasos"]) / entradas * 100, 1)
                if entradas
                else None,
            )
        return total_rutas, len(viajes)
