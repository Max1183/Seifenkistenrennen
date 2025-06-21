from django.urls import reverse
from rest_framework import status
from race_core.models import Team
from .test_api_base import APITestsBase # Importiere die Basisklasse

class TeamAPITests(APITestsBase):
    def test_list_teams_unauthenticated(self):
        self.unauthenticate()
        url = reverse('team-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)

    def test_retrieve_team_unauthenticated(self):
        self.unauthenticate()
        url = reverse('team-detail', kwargs={'pk': self.team1.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.team1.name)

    def test_create_team_unauthenticated_fails(self):
        self.unauthenticate()
        url = reverse('team-list')
        data = {"name": "Unauthorized Create"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_team_authenticated_admin(self):
        self.authenticate_as_admin()
        url = reverse('team-list')
        data = {"name": "Admin Created Team"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Team.objects.get(id=response.data['id']).name, data['name'])

    def test_update_team_authenticated_admin(self):
        self.authenticate_as_admin()
        url = reverse('team-detail', kwargs={'pk': self.team1.pk})
        updated_data = {"name": "Admin Updated Team Name"}
        response = self.client.put(url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.team1.refresh_from_db()
        self.assertEqual(self.team1.name, updated_data['name'])

    def test_partial_update_team_authenticated_admin(self):
        self.authenticate_as_admin()
        url = reverse('team-detail', kwargs={'pk': self.team1.pk})
        updated_data = {"name": "Admin Patched Team Name"}
        response = self.client.patch(url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.team1.refresh_from_db()
        self.assertEqual(self.team1.name, updated_data['name'])


    def test_delete_team_authenticated_admin(self):
        self.authenticate_as_admin()
        team_to_delete = Team.objects.create(name="Ephemeral Team")
        url = reverse('team-detail', kwargs={'pk': team_to_delete.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Team.objects.filter(pk=team_to_delete.pk).exists())

    def test_create_team_with_normal_user_fails_if_not_admin_permission(self):
        # Dieser Test ist relevant, wenn permission_classes = [permissions.IsAdminUser] wäre.
        # Bei IsAuthenticatedOrReadOnly sollte ein normaler User auch erstellen können.
        # Passe an, wenn deine Permissions anders sind.
        # Für IsAuthenticatedOrReadOnly:
        self.authenticate_as_normal_user()
        url = reverse('team-list')
        data = {"name": "Normal User Created Team"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)