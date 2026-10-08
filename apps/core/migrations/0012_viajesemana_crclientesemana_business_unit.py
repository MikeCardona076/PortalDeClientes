"""Añade dimensión de UDN a los agregados por cliente/semana.

`ViajeSemana` y `CRClienteSemana` pasan a ser por BusinessUnit para no mezclar
plazas (Tijuana, Cabos, Mexicali) al consolidar clientes que existen en varias.
"""

import django.db.models.deletion
from django.db import migrations, models


def backfill_business_unit(apps, schema_editor):
    BusinessUnit = apps.get_model("core", "BusinessUnit")
    ViajeSemana = apps.get_model("core", "ViajeSemana")
    CRClienteSemana = apps.get_model("core", "CRClienteSemana")

    bu = (
        BusinessUnit.objects.filter(code="set_tj2").first()
        or BusinessUnit.objects.order_by("id").first()
    )
    if bu is None:
        return
    ViajeSemana.objects.filter(business_unit__isnull=True).update(business_unit=bu)
    CRClienteSemana.objects.filter(business_unit__isnull=True).update(business_unit=bu)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_comentariosemana"),
    ]

    operations = [
        migrations.AddField(
            model_name="viajesemana",
            name="business_unit",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="viajes",
                to="core.businessunit",
            ),
        ),
        migrations.AddField(
            model_name="crclientesemana",
            name="business_unit",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="cr",
                to="core.businessunit",
            ),
        ),
        migrations.RunPython(backfill_business_unit, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="viajesemana",
            name="business_unit",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="viajes",
                to="core.businessunit",
            ),
        ),
        migrations.AlterField(
            model_name="crclientesemana",
            name="business_unit",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="cr",
                to="core.businessunit",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="viajesemana",
            unique_together={("cliente", "semana", "business_unit")},
        ),
        migrations.AlterUniqueTogether(
            name="crclientesemana",
            unique_together={("cliente", "semana", "business_unit", "window_mode")},
        ),
        # El índice viejo (semana, window_mode) queda cubierto por el
        # unique_together nuevo, que ya incluye business_unit.
        migrations.RemoveIndex(
            model_name="crclientesemana",
            name="core_crclie_semana__49db86_idx",
        ),
    ]
