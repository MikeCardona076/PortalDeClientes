"""Sincroniza una semana: `python manage.py sync_semana 2026 6 [--bunit set_tj2]`."""

from django.core.management.base import BaseCommand

from apps.sync.services import sync_semana


class Command(BaseCommand):
    help = "Sincroniza viajes/NS y CR (14d/7d) de una semana operativa."

    def add_arguments(self, parser):
        parser.add_argument("year", type=int)
        parser.add_argument("week", type=int)
        parser.add_argument("--bunit", action="append", dest="bunits", default=None)

    def handle(self, *args, **options):
        resumen = sync_semana(options["year"], options["week"], bunits=options["bunits"])
        self.stdout.write(self.style.SUCCESS(str(resumen)))
