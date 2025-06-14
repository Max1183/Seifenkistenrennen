from django.test import TestCase
from decimal import Decimal
from race_core.models import Team, Racer, RaceRun
from race_core.serializers import TeamSerializer, RacerSerializer, RaceRunSerializer

class TeamReadSerializerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team1 = Team.objects.create(name="Read Team One")
        cls.team2 = Team.objects.create(name="Read Team Two (No Racers)")
        cls.racer1_t1 = Racer.objects.create(first_name="Reader", last_name="One", team=cls.team1, start_number="R1", soapbox_class='LJ')
        cls.racer2_t1 = Racer.objects.create(first_name="Reader", last_name="Two", team=cls.team1, start_number="R2", soapbox_class='LS')

    def test_team_serializer_output(self):
        serializer = TeamSerializer(instance=self.team1)
        data = serializer.data
        self.assertEqual(data['name'], "Read Team One")
        self.assertEqual(data['racer_count'], 2)
        self.assertEqual(len(data['racers_info']), 2)
        self.assertIn(
            {'id': self.racer1_t1.id, 'first_name': 'Reader', 'last_name': 'One', 'start_number': 'R1'},
            data['racers_info']
        )

    def test_team_serializer_no_racers(self):
        serializer = TeamSerializer(instance=self.team2)
        data = serializer.data
        self.assertEqual(data['name'], "Read Team Two (No Racers)")
        self.assertEqual(data['racer_count'], 0)
        self.assertEqual(len(data['racers_info']), 0)

class RacerReadSerializerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="Racer Read Team")
        cls.racer = Racer.objects.create(
            first_name="Serialize", last_name="Me", team=cls.team,
            soapbox_class=Racer.SoapboxClass.X_KLASSE, start_number="S100"
        )
        RaceRun.objects.create(racer=cls.racer, run_type='H1', run_identifier=1, time_in_seconds="50.123")
        # This practice run is faster but should be ignored by the best_time_seconds property
        RaceRun.objects.create(racer=cls.racer, run_type='PR', run_identifier=1, time_in_seconds="49.000")

    def test_racer_serializer_output(self):
        serializer = RacerSerializer(instance=self.racer)
        data = serializer.data
        self.assertEqual(data['id'], self.racer.id)
        self.assertEqual(data['first_name'], "Serialize")
        self.assertEqual(data['last_name'], "Me")
        self.assertEqual(data['full_name'], "Serialize Me")
        self.assertEqual(data['soapbox_class'], Racer.SoapboxClass.X_KLASSE.value)
        self.assertEqual(data['soapbox_class_display'], Racer.SoapboxClass.X_KLASSE.label)
        self.assertEqual(data['team'], self.team.id)
        self.assertEqual(data['team_name'], self.team.name)
        self.assertEqual(data['start_number'], "S100")
        # The serializer should reflect the property's logic, ignoring the practice run.
        self.assertEqual(data['best_time_seconds'], "50.123")
        self.assertEqual(len(data['races']), 2)
        self.assertTrue(any(run['run_type'] == 'H1' for run in data['races']))
