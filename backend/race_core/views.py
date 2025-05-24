from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Team, Racer, RaceRun
from .serializers import (
    TeamSerializer, RacerSerializer, RaceRunSerializer,
    TeamWriteSerializer, RacerWriteSerializer, RaceRunWriteSerializer
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


class RacerViewSet(viewsets.ModelViewSet):
    queryset = Racer.objects.select_related('team').prefetch_related('races').all()
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
