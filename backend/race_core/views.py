from rest_framework import viewsets, permissions
from .models import Team, Racer
from .serializers import (
    TeamSerializer,
    RacerSerializer,
    TeamWriteSerializer,
    RacerWriteSerializer
)


class TeamViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows teams to be viewed or edited.
    """
    queryset = Team.objects.all().prefetch_related('racers')
    serializer_class = TeamSerializer

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TeamWriteSerializer
        return TeamSerializer

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class RacerViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows racers to be viewed or edited.
    """
    queryset = Racer.objects.select_related('team').all()
    serializer_class = RacerSerializer

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RacerWriteSerializer
        return RacerSerializer

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = Racer.objects.select_related('team').all()
        team_id = self.request.query_params.get('team_id')
        if team_id is not None:
            queryset = queryset.filter(team_id=team_id)
        return queryset
