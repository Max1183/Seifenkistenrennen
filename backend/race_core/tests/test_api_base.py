from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from race_core.models import Team, Racer, RaceRun

User = get_user_model()

class APITestsBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team1 = Team.objects.create(name="API Base Team")
        cls.racer1 = Racer.objects.create(
            first_name="ApiBase", last_name="Racer", team=cls.team1,
            soapbox_class='XKL', start_number="API_B1"
        )
        cls.racerun1 = RaceRun.objects.create(
            racer=cls.racer1, run_type='PR', run_identifier=1, time_in_seconds="70.000"
        )

        cls.admin_user = User.objects.create_superuser(
            username='apiadmin', email='apiadmin@example.com', password='apipassword123'
        )
        cls.normal_user = User.objects.create_user(
            username='apiuser', email='apiuser@example.com', password='apiuserpass123'
        )

    def setUp(self):
        self.client = APIClient()

    def _get_jwt_tokens_for_user(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

    def authenticate_as_admin(self):
        tokens = self._get_jwt_tokens_for_user(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')

    def authenticate_as_normal_user(self):
        tokens = self._get_jwt_tokens_for_user(self.normal_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')

    def unauthenticate(self):
        self.client.credentials()