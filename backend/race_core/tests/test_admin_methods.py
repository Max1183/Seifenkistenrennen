from django.test import TestCase
from django.contrib.admin.sites import AdminSite
from django.urls import reverse
from django.utils.html import format_html
from race_core.models import Team, Racer, RaceRun
from race_core.admin import TeamAdmin, RacerAdmin, RaceRunAdmin


class AdminMethodTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.site = AdminSite()
        cls.team1 = Team.objects.create(name="Admin Test Team")
        cls.racer1 = Racer.objects.create(
            first_name="AdminRacer", last_name="One", team=cls.team1,
            soapbox_class='LRJ', start_number="ADM1"
        )
        Racer.objects.create(
            first_name="AdminRacer", last_name="Two", team=cls.team1,
            soapbox_class='LRS', start_number="ADM2"
        )
        cls.run1 = RaceRun.objects.create(racer=cls.racer1, run_type='H1', run_identifier=1, time_in_seconds="30.000")
        RaceRun.objects.create(racer=cls.racer1, run_type='H2', run_identifier=1, time_in_seconds="29.500")

    def test_team_admin_racer_count_display(self):
        team_admin = TeamAdmin(model=Team, admin_site=self.site)
        self.assertEqual(team_admin.racer_count(self.team1), 2)  # Aus admin.py

    def test_racer_admin_best_time_display(self):
        racer_admin = RacerAdmin(model=Racer, admin_site=self.site)
        self.assertEqual(racer_admin.best_time_display(self.racer1), "29.500s")

        racer_no_time = Racer.objects.create(first_name="NoTime", last_name="Admin", soapbox_class='XKL')
        self.assertEqual(racer_admin.best_time_display(racer_no_time), "N/A")

    def test_racerun_admin_run_type_display(self):
        racerun_admin = RaceRunAdmin(model=RaceRun, admin_site=self.site)
        self.assertEqual(racerun_admin.run_type_display(self.run1), RaceRun.RaceRunType.HEAT_1.label)

    def test_racerun_admin_racer_link(self):
        racerun_admin = RaceRunAdmin(model=RaceRun, admin_site=self.site)
        expected_url = reverse("admin:race_core_racer_change", args=[self.racer1.id])
        # Wir müssen hier den String-Output der format_html Funktion vergleichen
        generated_link_str = str(racerun_admin.racer_link(self.run1))
        self.assertIn(expected_url, generated_link_str)
        self.assertIn(self.racer1.full_name, generated_link_str)