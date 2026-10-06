"""Siembra RefinamientoRuta para las rutas IN/N de un rango de fechas.

Ejemplo:
  python manage.py seed_refinamientos --desde 2026-06-08 --bunit set_tj2
"""

from django.core.management.base import BaseCommand

from apps.core.models import RefinamientoRuta, ServicioRutaSemana


class Command(BaseCommand):
    help = "Crea RefinamientoRuta para cada (grupo, ruta) IN/N del rango."

    def add_arguments(self, parser):
        parser.add_argument("--desde", default="2026-06-08", help="Fecha ISO mínima de servicio.")
        parser.add_argument("--hasta", default=None, help="Fecha ISO máxima de servicio.")
        parser.add_argument("--bunit", default="set_tj2")
        parser.add_argument("--grupo", default=None, help="Restringe a un group exacto.")
        parser.add_argument(
            "--tol", type=int, default=200, help="Tolerancia en metros (plataforma=200)."
        )

    def handle(self, *args, **o):
        qs = ServicioRutaSemana.objects.filter(
            business_unit__code=o["bunit"],
            shift="IN",
            tipo_viaje="N",
            fecha_inicio__gte=o["desde"],
        ).exclude(ruta_seq="")
        if o["hasta"]:
            qs = qs.filter(fecha_inicio__lte=o["hasta"])
        if o["grupo"]:
            qs = qs.filter(grupo__group=o["grupo"])

        pares = set(qs.values_list("grupo_id", "ruta_seq"))
        existentes = set(
            RefinamientoRuta.objects.filter(
                grupo__business_unit__code=o["bunit"]
            ).values_list("grupo_id", "ruta_seq")
        )
        nuevos = [
            RefinamientoRuta(grupo_id=g, ruta_seq=r, tol_m=o["tol"])
            for (g, r) in pares
            if (g, r) not in existentes
        ]
        RefinamientoRuta.objects.bulk_create(nuevos, ignore_conflicts=True)
        self.stdout.write(
            self.style.SUCCESS(
                f"Refinamientos: {len(pares)} rutas, {len(nuevos)} nuevos, "
                f"{len(pares) - len(nuevos)} ya existían."
            )
        )
