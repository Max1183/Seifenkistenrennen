# Generated by Django 5.2.1 on 2025-05-24 12:27

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('race_core', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='racer',
            name='date_of_birth',
        ),
        migrations.AddField(
            model_name='racer',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='Created At'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='racer',
            name='soapbox_class',
            field=models.CharField(choices=[('LJ', 'Luftreifen Junior'), ('LS', 'Luftreifen Senior'), ('HJ', 'Hartreifen Junior'), ('HS', 'Hartreifen Senior'), ('XK', 'X-Klasse'), ('VT', 'Veteranen'), ('UN', 'Unknown')], default='UN', help_text='The class the racer is competing in.', max_length=2, verbose_name='Soapbox Class'),
        ),
        migrations.AddField(
            model_name='racer',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Updated At'),
        ),
        migrations.AddField(
            model_name='team',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='Created At'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='team',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Updated At'),
        ),
        migrations.CreateModel(
            name='RaceRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time_in_seconds', models.DecimalField(blank=True, decimal_places=3, help_text='Time taken for this run in seconds (e.g., 45.123).', max_digits=6, null=True, verbose_name='Time (seconds)')),
                ('disqualified', models.BooleanField(default=False, verbose_name='Disqualified')),
                ('notes', models.TextField(blank=True, null=True, verbose_name='Notes')),
                ('run_identifier', models.PositiveSmallIntegerField(default=1, help_text='Identifier for the run (e.g., 1 for first attempt, 2 for second of a specific type).', verbose_name='Run Identifier')),
                ('run_type', models.CharField(choices=[('PR', 'Practice'), ('H1', 'Heat 1'), ('H2', 'Heat 2')], default='PR', help_text='Type of race run (e.g., Practice, Heat 1, Heat 2).', max_length=2, verbose_name='Run Type')),
                ('recorded_at', models.DateTimeField(auto_now_add=True, verbose_name='Recorded At')),
                ('racer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='races', to='race_core.racer', verbose_name='Racer')),
            ],
            options={
                'verbose_name': 'Race Run',
                'verbose_name_plural': 'Race Runs',
                'ordering': ['racer__last_name', 'racer__first_name', 'run_type', 'run_identifier'],
                'unique_together': {('racer', 'run_type', 'run_identifier')},
            },
        ),
    ]
