from django.db import migrations


def forwards(apps, schema_editor):
    PerfilUsuario = apps.get_model("core", "PerfilUsuario")
    BusinessUnit = apps.get_model("core", "BusinessUnit")

    bu = BusinessUnit.objects.filter(code="set_tj2").first()
    if bu is not None:
        for perfil in PerfilUsuario.objects.all():
            perfil.business_units.add(bu)

    PerfilUsuario.objects.filter(user__is_superuser=True).update(
        debe_cambiar_password=False
    )
    PerfilUsuario.objects.filter(es_admin=True).update(debe_cambiar_password=False)


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_perfilusuario_business_units_perfilusuario_correos_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
