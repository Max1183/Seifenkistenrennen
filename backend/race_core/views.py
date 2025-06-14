from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend

from .models import Team, Racer, RaceRun, Soapbox
from .serializers import (
    TeamSerializer, RacerSerializer, RaceRunSerializer, TeamWriteSerializer, RacerWriteSerializer,
    RaceRunWriteSerializer, SoapboxSerializer, SoapboxWriteSerializer
)


class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all().prefetch_related('racers')
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TeamWriteSerializer
        return TeamSerializer


class SoapboxViewSet(viewsets.ModelViewSet):
    queryset = Soapbox.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return SoapboxWriteSerializer
        return SoapboxSerializer


class RacerViewSet(viewsets.ModelViewSet):
    queryset = Racer.objects.select_related('team', 'soapbox').prefetch_related('races').all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'team': ['exact'],
        'soapbox_class': ['exact'],
        'last_name': ['icontains'],
        'first_name': ['icontains'],
        'start_number': ['exact'],
    }
    search_fields = ['first_name', 'last_name', 'team__name', 'start_number']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RacerWriteSerializer
        return RacerSerializer


class RaceRunViewSet(viewsets.ModelViewSet):
    queryset = RaceRun.objects.select_related('racer', 'racer__team').all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'racer': ['exact'],
        'racer__team': ['exact'],
        'run_type': ['exact'],
        'disqualified': ['exact'],
    }

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RaceRunWriteSerializer
        return RaceRunSerializer
