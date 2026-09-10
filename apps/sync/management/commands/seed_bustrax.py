"""Crea las UDN base y (opcional) los grupos/clientes desde la API.

`python manage.py seed_bustrax [--bunit set_tj2 ...]`
"""

from django.core.management.base import BaseCommand

from apps.bustrax import client as api
from apps.bustrax.cr import client_base
from apps.core.models import BusinessUnit, Cliente, GrupoCliente

NOMBRES = {
    "set_tj2": "SETTEPI Tijuana 2",
    "set_tj1": "SETTEPI Tijuana 1",
    "set_mxl": "SETTEPI Mexicali",
    "set_cab": "SETTEPI Los Cabos",
    "set_qui": "SETTEPI San Quintin",
}


class Command(BaseCommand):
    help = "Registra UDN y grupos/clientes desde get_groups."

    def add_arguments(self, parser):
        parser.add_argument("--bunit", action="append", dest="bunits", default=None)

    def handle(self, *args, **options):
        bunits = options["bunits"] or ["set_tj2"]
        for code in bunits:
            bu, _ = BusinessUnit.objects.update_or_create(
                code=code, defaults={"nombre": NOMBRES.get(code, code)}
            )
            self.stdout.write(f"UDN {code} ok")
            try:
                grupos = api.get_groups(code)
            except api.BustraxError as exc:
                self.stderr.write(f"  get_groups {code}: {exc}")
                continue
            for g in grupos:
                desc = g.get("description") or ""
                if not desc:
                    continue
                cliente, _ = Cliente.objects.get_or_create(nombre=client_base(desc))
                GrupoCliente.objects.update_or_create(
                    group=desc,
                    defaults={
                        "cliente": cliente,
                        "gcode": g.get("gcode", ""),
                        "business_unit": bu,
                    },
                )
            self.stdout.write(f"  grupos: {len(grupos)}")
        self.stdout.write(self.style.SUCCESS("Seed completo."))
