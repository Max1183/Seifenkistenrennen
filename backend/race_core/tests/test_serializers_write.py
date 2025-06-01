from django.test import TestCase
from decimal import Decimal
from rest_framework.exceptions import ValidationError as DRFValidationError
from race_core.models import Team, Racer, RaceRun
from race_core.serializers import TeamWriteSerializer, RacerWriteSerializer, RaceRunWriteSerializer


class TeamWriteSerializerTests(TestCase):
    def test_team_write_serializer_valid(self):
        data = {"name": "Valid Team"}
        serializer = TeamWriteSerializer(data=data)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        team = serializer.save()
        self.assertEqual(team.name, "Valid Team")

    def test_team_write_serializer_duplicate_name(self):
        Team.objects.create(name="Existing Team")
        data = {"name": "Existing Team"}
        serializer = TeamWriteSerializer(data=data)
        with self.assertRaises(DRFValidationError) as cm:
            serializer.is_valid(raise_exception=True)
        self.assertIn('name', cm.exception.detail)


class RacerWriteSerializerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="Racer Write Team")

    def test_racer_write_serializer_valid(self):
        data = {
            "first_name": "Write", "last_name": "Me",
            "soapbox_class": Racer.SoapboxClass.LUFTREIFEN_JUNIOR.value,
            "team": self.team.id, "start_number": "W101"
        }
        serializer = RacerWriteSerializer(data=data)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        racer = serializer.save()
        self.assertEqual(racer.first_name, "Write")
        self.assertEqual(racer.team, self.team)

    def test_racer_write_serializer_invalid_team_id(self):
        data = {
            "first_name": "No", "last_name": "Team",
            "soapbox_class": 'LJ', "team": 9999, "start_number": "W102"
        }
        serializer = RacerWriteSerializer(data=data)
        with self.assertRaises(DRFValidationError) as cm:
            serializer.is_valid(raise_exception=True)
        self.assertIn('team', cm.exception.detail)

    def test_racer_write_serializer_duplicate_start_number(self):
        Racer.objects.create(first_name="Ex", last_name="Num", soapbox_class='LS', start_number="W103")
        data = {
            "first_name": "Dup", "last_name": "Num",
            "soapbox_class": 'HS', "start_number": "W103"
        }
        serializer = RacerWriteSerializer(data=data)
        with self.assertRaises(DRFValidationError):
            serializer.is_valid(raise_exception=True)
        self.assertIn('start_number', serializer.errors)


class RaceRunWriteSerializerValidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="RaceRun Write Validations")
        cls.racer1 = Racer.objects.create(first_name="R1", last_name="Val", team=cls.team, soapbox_class='LJ',
                                          start_number="V1")
        cls.racer2 = Racer.objects.create(first_name="R2", last_name="Val", team=cls.team, soapbox_class='LS',
                                          start_number="V2")
        cls.existing_run = RaceRun.objects.create(racer=cls.racer1, run_type='H1', run_identifier=1,
                                                  time_in_seconds="10.000")

    def test_create_with_racer_id(self):
        data = {"racer_id": self.racer2.id, "run_type": "H1", "run_identifier": 1, "time_in_seconds": "20.000"}
        serializer = RaceRunWriteSerializer(data=data)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        instance = serializer.save()
        self.assertEqual(instance.racer, self.racer2)

    def test_create_with_racer_start_number(self):
        data = {"racer_start_number": self.racer2.start_number, "run_type": "H2", "run_identifier": 1,
                "time_in_seconds": "21.000"}
        serializer = RaceRunWriteSerializer(data=data)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        instance = serializer.save()
        self.assertEqual(instance.racer, self.racer2)

    def test_create_with_direct_racer_pk(self):
        data = {"racer_id": self.racer2.id, "run_type": "PR", "run_identifier": 1, "time_in_seconds": "22.000"}
        serializer = RaceRunWriteSerializer(data=data)
        # This relies on _get_racer_instance_from_input_data to handle 'racer' key
        self.assertTrue(serializer.is_valid(raise_exception=True))
        instance = serializer.save()
        self.assertEqual(instance.racer, self.racer2)

    def test_create_missing_racer_identifier_fails(self):
        data = {"run_type": "H1", "run_identifier": 1, "time_in_seconds": "20.000"}
        serializer = RaceRunWriteSerializer(data=data)
        with self.assertRaises(DRFValidationError) as cm:
            serializer.is_valid(raise_exception=True)
        self.assertTrue(any('A racer must be identified' in str(e) for e in (
            cm.exception.detail if isinstance(cm.exception.detail, list) else cm.exception.detail.get(
                'non_field_errors', []))))

    def test_create_invalid_racer_id_fails(self):
        data = {"racer_id": 9999, "run_type": "H1", "run_identifier": 1}
        serializer = RaceRunWriteSerializer(data=data)
        with self.assertRaises(DRFValidationError) as cm:
            serializer.is_valid(raise_exception=True)
        self.assertIn('racer_id', cm.exception.detail)

    def test_create_invalid_racer_start_number_fails(self):
        data = {"racer_start_number": "INVALID99", "run_type": "H1", "run_identifier": 1}
        serializer = RaceRunWriteSerializer(data=data)
        with self.assertRaises(DRFValidationError) as cm:
            serializer.is_valid(raise_exception=True)
        self.assertIn('racer_start_number', cm.exception.detail)

    def test_validate_unique_together_on_create(self):
        data = {"racer_id": self.racer1.id, "run_type": "H1", "run_identifier": 1}
        serializer = RaceRunWriteSerializer(data=data)
        with self.assertRaises(DRFValidationError) as cm:
            serializer.is_valid(raise_exception=True)
        self.assertIn('unique', cm.exception.detail[0].code if isinstance(cm.exception.detail, list) else
        cm.exception.detail.get('non_field_errors', [{}])[0].code)

    def test_validate_unique_together_on_update_no_conflict(self):
        serializer = RaceRunWriteSerializer(instance=self.existing_run, data={"time_in_seconds": "11.000"},
                                            partial=True)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        serializer.save()
        self.existing_run.refresh_from_db()
        self.assertEqual(self.existing_run.time_in_seconds, Decimal("11.000"))

    def test_validate_unique_together_on_update_causes_conflict(self):
        # self.existing_run: racer1, H1, 1
        # new_run: racer2, H1, 1
        new_run = RaceRun.objects.create(racer=self.racer2, run_type='H1', run_identifier=1, time_in_seconds="12.000")

        # Try to update new_run to have the same racer as existing_run (causing conflict)
        serializer = RaceRunWriteSerializer(instance=new_run, data={"racer_id": self.racer1.id}, partial=True)
        with self.assertRaises(DRFValidationError) as cm:
            serializer.is_valid(raise_exception=True)
        self.assertIn('unique', cm.exception.detail[0].code if isinstance(cm.exception.detail, list) else
        cm.exception.detail.get('non_field_errors', [{}])[0].code)

    def test_validate_disqualified_and_time(self):
        data_dq_with_time = {"racer_id": self.racer1.id, "run_type": "H2", "run_identifier": 1, "disqualified": True,
                             "time_in_seconds": "10.000"}
        serializer_dq = RaceRunWriteSerializer(data=data_dq_with_time)
        with self.assertRaises(DRFValidationError) as cm:
            serializer_dq.is_valid(raise_exception=True)
        self.assertIn('time_in_seconds', cm.exception.detail)

        data_dq_no_time = {"racer_id": self.racer1.id, "run_type": "H2", "run_identifier": 2, "disqualified": True,
                           "time_in_seconds": None}
        serializer_no_time = RaceRunWriteSerializer(data=data_dq_no_time)
        self.assertTrue(serializer_no_time.is_valid(raise_exception=True))

    def test_update_sets_disqualified_nulls_time(self):
        run = RaceRun.objects.create(racer=self.racer1, run_type='PR', run_identifier=3, time_in_seconds="30.000")
        serializer = RaceRunWriteSerializer(instance=run, data={'disqualified': True}, partial=True)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        updated_run = serializer.save()
        self.assertTrue(updated_run.disqualified)
        self.assertIsNone(updated_run.time_in_seconds)

    def test_to_representation_for_write_serializer(self):
        run = RaceRun.objects.create(racer=self.racer1, run_type='PR', run_identifier=4, time_in_seconds="30.000")
        write_serializer = RaceRunWriteSerializer(instance=run)
        data = write_serializer.data  # Triggers to_representation

        self.assertEqual(data['racer'], self.racer1.id)
        self.assertEqual(data['racer_name'], self.racer1.full_name)
        self.assertEqual(data['run_type_display'], run.get_run_type_display())