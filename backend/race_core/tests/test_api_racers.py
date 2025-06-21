from django.urls import reverse
from rest_framework import status
from race_core.models import Racer, Team
from .test_api_base import APITestsBase

class RacerAPITests(APITestsBase):
    def test_list_racers_unauthenticated(self):
        self.unauthenticate()
        url = reverse('racer-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)

    def test_create_racer_authenticated_admin(self):
        self.authenticate_as_admin()
        url = reverse('racer-list')
        new_racer_data = {
            "first_name": "APIAdmin", "last_name": "Racer",
            "soapbox_class": Racer.SoapboxClass.LUFTREIFEN_SENIOR.value,
            "start_number": "API_R1", "team": self.team1.id
        }
        response = self.client.post(url, new_racer_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Racer.objects.get(id=response.data['id']).first_name, "APIAdmin")

    def test_filter_racers_by_team_id(self):
        self.unauthenticate()
        team_for_filter = Team.objects.create(name="FilterTeam")
        racer_in_filter_team = Racer.objects.create(
            first_name="Filtered", last_name="Racer", team=team_for_filter, soapbox_class='HJ'
        )
        url = reverse('racer-list')
        response = self.client.get(url, {'team': team_for_filter.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], racer_in_filter_team.id)

    def test_filter_racers_by_soapbox_class(self):
        self.unauthenticate()
        url = reverse('racer-list')
        response = self.client.get(url, {'soapbox_class': Racer.SoapboxClass.X_KLASSE.value})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1) # self.racer1 ist X_KLASSE
        for racer_data in response.data:
            self.assertEqual(racer_data['soapbox_class'], Racer.SoapboxClass.X_KLASSE.value)
