from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TeamViewSet, RacerViewSet, RaceRunViewSet, SoapboxViewSet

router = DefaultRouter()
router.register(r'teams', TeamViewSet, basename='team')
router.register(r'soapboxes', SoapboxViewSet, basename='soapbox')
router.register(r'racers', RacerViewSet, basename='racer')
router.register(r'raceruns', RaceRunViewSet, basename='racerun')

urlpatterns = [
    path('', include(router.urls)),
]
