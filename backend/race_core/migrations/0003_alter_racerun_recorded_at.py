# Generated by Django 5.2.1 on 2025-06-09 12:29

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('race_core', '0002_remove_racer_date_of_birth_racer_created_at_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='racerun',
            name='recorded_at',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Recorded At'),
        ),
    ]
