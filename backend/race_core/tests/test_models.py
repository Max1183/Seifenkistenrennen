from django.test import TestCase
from django.db import IntegrityError
from decimal import Decimal
from race_core.models import Team, Racer, RaceRun


class TeamModelTests(TestCase):
    def test_team_creation_and_str(self):
        team = Team.objects.create(name="Team Phoenix")
        self.assertEqual(team.name, "Team Phoenix")
        self.assertEqual(str(team), "Team Phoenix")
        self.assertIsNotNone(team.created_at)
        self.assertIsNotNone(team.updated_at)


class RacerModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="Test Team Racers")
        cls.racer = Racer.objects.create(
            first_name="Lightning",
            last_name="McQueen",
            soapbox_class=Racer.SoapboxClass.X_KLASSE,
            team=cls.team,
            start_number="95"
        )
        # Add runs to test the best_time logic
        RaceRun.objects.create(racer=cls.racer, run_type='H1', run_identifier=1, time_in_seconds="40.100")
        RaceRun.objects.create(racer=cls.racer, run_type='H2', run_identifier=1, time_in_seconds="39.900")
        # This practice run is the fastest but should be ignored
        RaceRun.objects.create(racer=cls.racer, run_type='PR', run_identifier=1, time_in_seconds="35.000")
        # This disqualified run should be ignored
        RaceRun.objects.create(racer=cls.racer, run_type='H1', run_identifier=2, time_in_seconds="38.000", disqualified=True)


    def test_racer_creation_and_str(self):
        self.assertEqual(self.racer.first_name, "Lightning")
        self.assertEqual(self.racer.last_name, "McQueen")
        self.assertEqual(str(self.racer), "Lightning McQueen")
        self.assertEqual(self.racer.team, self.team)
        self.assertEqual(self.racer.start_number, "95")
        self.assertIsNotNone(self.racer.created_at)
        self.assertIsNotNone(self.racer.updated_at)

    def test_racer_full_name_property(self):
        self.assertEqual(self.racer.full_name, "Lightning McQueen")

    def test_racer_best_time_seconds_property(self):
        # The best time should be from H2 (39.900), not the faster PR run (35.000).
        self.assertEqual(self.racer.best_time_seconds, Decimal("39.900"))

    def test_racer_best_time_seconds_no_valid_runs(self):
        racer_no_runs = Racer.objects.create(first_name="No", last_name="Runs", soapbox_class='LJ')
        self.assertIsNone(racer_no_runs.best_time_seconds)

        racer_dq_runs = Racer.objects.create(first_name="DQ", last_name="Only", soapbox_class='LS')
        RaceRun.objects.create(racer=racer_dq_runs, run_type='H1', run_identifier=1, disqualified=True)
        self.assertIsNone(racer_dq_runs.best_time_seconds)

    def test_racer_start_number_unique_constraint(self):
        with self.assertRaises(IntegrityError):
            Racer.objects.create(
                first_name="Duplicate",
                last_name="StartNr",
                soapbox_class='VT',
                start_number="95"  # Bereits von self.racer verwendet
            )


class RaceRunModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="Test Team RaceRuns")
        cls.racer = Racer.objects.create(
            first_name="Chick",
            last_name="Hicks",
            soapbox_class='XK',
            team=cls.team,
            start_number="86"
        )
        cls.racerun = RaceRun.objects.create(
            racer=cls.racer,
            run_type=RaceRun.RaceRunType.HEAT_1,
            run_identifier=1,
            time_in_seconds="42.500",
            disqualified=False
        )

    def test_racerun_creation_and_str(self):
        self.assertEqual(self.racerun.racer, self.racer)
        self.assertEqual(float(self.racerun.time_in_seconds), Decimal("42.500"))
        self.assertFalse(self.racerun.disqualified)
        self.assertEqual(str(self.racerun), "Chick Hicks - Heat 1 Run 1 - 42.500s")
        self.assertIsNotNone(self.racerun.recorded_at)

    def test_racerun_str_disqualified(self):
        dq_run = RaceRun.objects.create(racer=self.racer, run_type='H2', run_identifier=1, disqualified=True)
        self.assertEqual(str(dq_run), "Chick Hicks - Heat 2 Run 1 - DQ")

    def test_racerun_str_no_time(self):
        no_time_run = RaceRun.objects.create(racer=self.racer, run_type='PR', run_identifier=1, time_in_seconds=None)
        self.assertEqual(str(no_time_run), "Chick Hicks - Practice Run 1 - N/A")

    def test_racerun_unique_together_constraint(self):
        with self.assertRaises(IntegrityError):
            RaceRun.objects.create(
                racer=self.racer,
                run_type=RaceRun.RaceRunType.HEAT_1,
                run_identifier=1,  # Dieselbe Kombination wie self.racerun
                time_in_seconds="50.000"
            )
