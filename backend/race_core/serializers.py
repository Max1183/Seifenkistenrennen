from rest_framework import serializers
from .models import Team, Racer, RaceRun


class RaceRunSerializer(serializers.ModelSerializer):
    racer_name = serializers.CharField(source='racer.full_name', read_only=True)
    run_type_display = serializers.CharField(source='get_run_type_display', read_only=True)

    class Meta:
        model = RaceRun
        fields = [
            'id',
            'racer',
            'racer_name',
            'time_in_seconds',
            'disqualified',
            'notes',
            'run_identifier',
            'run_type',
            'run_type_display',
        ]


class RacerSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True, allow_null=True)
    best_time_seconds = serializers.DecimalField(max_digits=6, decimal_places=3, read_only=True)
    soapbox_class_display = serializers.CharField(source='get_soapbox_class_display', read_only=True)
    races = RaceRunSerializer(many=True, read_only=True)

    class Meta:
        model = Racer
        fields = [
            'id',
            'first_name',
            'last_name',
            'full_name',
            'soapbox_class',
            'soapbox_class_display',
            'team',
            'team_name',
            'start_number',
            'best_time_seconds',
            'races',
        ]
        read_only_fields = ['id', 'full_name', 'best_time_seconds', 'team_name', 'soapbox_class_display', 'races']


class TeamSerializer(serializers.ModelSerializer):
    racers_info = serializers.SerializerMethodField(read_only=True)
    racer_count = serializers.IntegerField(source='racers.count', read_only=True)

    class Meta:
        model = Team
        fields = [
            'id',
            'name',
            'racer_count',
            'racers_info',
        ]
        read_only_fields = ['id', 'racer_count', 'racers_info']

    def get_racers_info(self, obj):
        return obj.racers.values('id', 'first_name', 'last_name')


class TeamWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['name']


class RacerWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Racer
        fields = [
            'first_name',
            'last_name',
            'soapbox_class',
            'team',
            'start_number',
        ]


class RaceRunWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RaceRun
        fields = [
            'racer',
            'time_in_seconds',
            'disqualified',
            'notes',
            'run_identifier',
            'run_type',
        ]

    def validate(self, data):
        if data.get('disqualified') and data.get('time_in_seconds') is not None:
            data['time_in_seconds'] = None
        elif not data.get('disqualified') and data.get('time_in_seconds') is None:
            pass
        return data
