from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_alter_paradarutasemana_unique_together"),
    ]

    operations = [
        migrations.AddField(
            model_name="paradarutasemana",
            name="detenidas",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="paradarutasemana",
            name="idle_seg",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="paradarutasemana",
            name="vel_min",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
