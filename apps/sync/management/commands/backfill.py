"""Backfill de un año: `python manage.py backfill 2026 [--desde 1] [--hasta 36]`."""

from django.core.management.base import BaseCommand

from apps.sync.services import backfill


class Command(BaseCommand):
    help = "Sincroniza un rango de semanas de un año."

    def add_arguments(self, parser):
        parser.add_argument("year", type=int)
        parser.add_argument("--desde", type=int, default=1)
        parser.add_argument("--hasta", type=int, default=None)
        parser.add_argument("--bunit", action="append", dest="bunits", default=None)

    def handle(self, *args, **options):
        resultados = backfill(
            options["year"],
            week_from=options["desde"],
            week_to=options["hasta"],
            bunits=options["bunits"],
        )
        for r in resultados:
            self.stdout.write(f"S{r['week']}: {r['bunits']}")
        self.stdout.write(self.style.SUCCESS(f"Listo: {len(resultados)} semanas."))
