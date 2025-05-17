from rest_framework import serializers
from .models import Team, Racer


class RacerSerializer(serializers.ModelSerializer):
    age = serializers.IntegerField(source='get_age', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)

    class Meta:
        model = Racer
        fields = [
            'id',
            'first_name',
            'last_name',
            'full_name',
            'date_of_birth',
            'age',
            'team',
            'team_name',
        ]
        read_only_fields = ['id', 'full_name']


class TeamSerializer(serializers.ModelSerializer):
    racers = RacerSerializer(many=True, read_only=True)
    racer_count = serializers.IntegerField(source='racers.count', read_only=True)

    class Meta:
        model = Team
        fields = [
            'id',
            'name',
            'racers',
            'racer_count',
        ]
        read_only_fields = ['id']


class RacerWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Racer
        fields = [
            'first_name',
            'last_name',
            'date_of_birth',
            'team',
        ]
    def validate_date_of_birth(self, value):
        from datetime import date
        if value > date.today():
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        return value


class TeamWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['name']
