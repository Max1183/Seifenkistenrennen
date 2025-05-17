from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TeamViewSet, RacerViewSet

router = DefaultRouter()
router.register(r'teams', TeamViewSet, basename='team')
router.register(r'racers', RacerViewSet, basename='racer')

urlpatterns = [
    path('', include(router.urls)),
]