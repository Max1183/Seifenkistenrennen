from django.urls import reverse
from rest_framework import status
from race_core.models import RaceRun, Racer
from .test_api_base import APITestsBase


class RaceRunAPITests(APITestsBase):
    def test_list_raceruns_unauthenticated(self):
        self.unauthenticate()
        url = reverse('racerun-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)

    def test_create_racerun_with_racer_id_admin(self):
        self.authenticate_as_admin()
        url = reverse('racerun-list')
        data = {
            "racer_id": self.racer1.id,
            "run_type": RaceRun.RaceRunType.HEAT_1.value,
            "run_identifier": 2,
            "time_in_seconds": "55.555"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(RaceRun.objects.get(id=response.data['id']).racer, self.racer1)

    def test_create_racerun_with_start_number_admin(self):
        self.authenticate_as_admin()
        url = reverse('racerun-list')
        data = {
            "racer_start_number": self.racer1.start_number,
            "run_type": RaceRun.RaceRunType.HEAT_2.value,
            "run_identifier": 1,
            "time_in_seconds": "50.123"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(RaceRun.objects.get(id=response.data['id']).racer, self.racer1)

    def test_create_racerun_with_direct_racer_pk_admin(self):
        self.authenticate_as_admin()
        url = reverse('racerun-list')
        data = {
            "racer_id": self.racer1.id,  # Direkte PK, wird von _get_racer_instance_from_input_data behandelt
            "run_type": RaceRun.RaceRunType.PRACTICE.value,
            "run_identifier": 2,
            "time_in_seconds": "51.000"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(RaceRun.objects.get(id=response.data['id']).racer, self.racer1)

    def test_create_racerun_duplicate_returns_400(self):
        self.authenticate_as_admin()
        url = reverse('racerun-list')
        # self.racerun1: racer1, PR, 1
        data_duplicate = {
            "racer_id": self.racer1.id,
            "run_type": RaceRun.RaceRunType.PRACTICE.value,
            "run_identifier": 1,
            "time_in_seconds": "70.000"
        }
        response = self.client.post(url, data_duplicate, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn("already exists", str(response.data.get('non_field_errors', [''])[0]).lower())

    def test_create_racerun_missing_racer_identifier_returns_400(self):
        self.authenticate_as_admin()
        url = reverse('racerun-list')
        data = {"run_type": "H1", "run_identifier": 10, "time_in_seconds": "30.000"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertTrue(any('A racer must be identified' in str(e) for e in (
            response.data if isinstance(response.data, list) else response.data.get('non_field_errors', []))))

    def test_update_racerun_time_admin(self):
        self.authenticate_as_admin()
        url = reverse('racerun-detail', kwargs={'pk': self.racerun1.pk})
        data = {"time_in_seconds": "59.999"}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.racerun1.refresh_from_db()
        self.assertEqual(str(self.racerun1.time_in_seconds), "59.999")

    def test_update_racerun_to_disqualified_nulls_time_admin(self):
        self.authenticate_as_admin()
        run_with_time = RaceRun.objects.create(
            racer=self.racer1, run_type='H1', run_identifier=3, time_in_seconds="40.000"
        )
        url = reverse('racerun-detail', kwargs={'pk': run_with_time.pk})
        data = {"disqualified": True}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        run_with_time.refresh_from_db()
        self.assertTrue(run_with_time.disqualified)
        self.assertIsNone(run_with_time.time_in_seconds)
        self.assertIsNone(response.data.get('time_in_seconds'))

    def test_filter_raceruns_by_racer_team(self):
        self.unauthenticate()
        url = reverse('racerun-list')
        response = self.client.get(url, {'racer__team': self.team1.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)
        for run_data in response.data:
            racer = Racer.objects.get(pk=run_data['racer'])
            self.assertEqual(racer.team, self.team1)