from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_paradarutasemana_detenidas_vel_min_idle_seg"),
    ]

    operations = [
        migrations.AddField(
            model_name="paradarutasemana",
            name="servicios_gps",
            field=models.IntegerField(default=0),
        ),
    ]
