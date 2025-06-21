from rest_framework import serializers
from .models import Team, Racer, RaceRun, Soapbox
from django.utils.translation import gettext_lazy as _


class RaceRunSerializer(serializers.ModelSerializer):
    racer_name = serializers.CharField(source='racer.full_name', read_only=True)
    run_type_display = serializers.CharField(source='get_run_type_display', read_only=True)
    racer_start_number = serializers.CharField(source='racer.start_number', read_only=True, allow_null=True)

    class Meta:
        model = RaceRun
        fields = [
            'id',
            'racer',
            'racer_name',
            'racer_start_number',
            'time_in_seconds',
            'disqualified',
            'notes',
            'run_identifier',
            'run_type',
            'run_type_display',
            'recorded_at',
        ]


class RacerSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True, allow_null=True)
    soapbox_name = serializers.CharField(source='soapbox.name', read_only=True, allow_null=True)
    best_time_seconds = serializers.DecimalField(max_digits=6, decimal_places=3, read_only=True, allow_null=True)
    soapbox_class_display = serializers.CharField(source='get_soapbox_class_display', read_only=True)
    races = RaceRunSerializer(many=True, read_only=True)

    class Meta:
        model = Racer
        fields = [
            'id',
            'first_name',
            'last_name',
            'full_name',
            'soapbox',
            'soapbox_name',
            'soapbox_class',
            'soapbox_class_display',
            'team',
            'team_name',
            'start_number',
            'best_time_seconds',
            'races',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'full_name', 'best_time_seconds', 'team_name', 'soapbox_class_display', 'races', 'soapbox_name']


class SoapboxSerializer(serializers.ModelSerializer):

    class Meta:
        model = Soapbox
        fields = [
            'id',
            'name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id']


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
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'racer_count', 'racers_info']

    def get_racers_info(self, obj):
        return obj.racers.values('id', 'first_name', 'last_name', 'start_number')


class TeamWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = [
            'id',
            'name',
        ]
        read_only_fields = ['id']


class SoapboxWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Soapbox
        fields = [
            'id',
            'name',
        ]
        read_only_fields = ['id']


class RacerWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Racer
        fields = [
            'id',
            'first_name',
            'last_name',
            'soapbox_class',
            'team',
            'start_number',
            'soapbox',
        ]
        read_only_fields = ['id']


class RaceRunWriteSerializer(serializers.ModelSerializer):
    racer_id = serializers.IntegerField(
        required=False, allow_null=True, write_only=True, label=_("Racer ID")
    )
    racer_start_number = serializers.CharField(
        required=False, allow_null=True, write_only=True, max_length=10, label=_("Racer Start Number")
    )
    recorded_at = serializers.DateTimeField(required=False)

    class Meta:
        model = RaceRun
        fields = [
            'racer_id',
            'racer_start_number',
            'time_in_seconds',
            'disqualified',
            'notes',
            'run_identifier',
            'run_type',
            'recorded_at',
        ]

    def _get_racer_instance_from_input_data(self, input_data_dict):
        racer_id_input = input_data_dict.get('racer_id')
        racer_start_number_input = input_data_dict.get('racer_start_number')
        racer_pk_from_direct_input = input_data_dict.get('racer')  # Falls 'racer' als PK gesendet wird

        identified_racer = None

        if racer_pk_from_direct_input is not None:
            try:
                racer_pk = int(racer_pk_from_direct_input)
                identified_racer = Racer.objects.get(id=racer_pk)
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    {'racer': _(f"Invalid value for Racer PK: '{racer_pk_from_direct_input}'. Must be an integer.")})
            except Racer.DoesNotExist:
                raise serializers.ValidationError(
                    {'racer': _(f"Racer with PK {racer_pk_from_direct_input} not found.")})
        elif racer_id_input is not None:
            try:
                identified_racer = Racer.objects.get(id=racer_id_input)
            except Racer.DoesNotExist:
                raise serializers.ValidationError({'racer_id': _(f"Racer with ID {racer_id_input} not found.")})
        elif racer_start_number_input is not None:
            try:
                identified_racer = Racer.objects.get(start_number__iexact=str(racer_start_number_input))
            except Racer.DoesNotExist:
                raise serializers.ValidationError(
                    {'racer_start_number': _(f"Racer with start number '{racer_start_number_input}' not found.")})
            except Racer.MultipleObjectsReturned:
                raise serializers.ValidationError(
                    {'racer_start_number': _(f"Multiple racers found with start number '{racer_start_number_input}'.")})

        return identified_racer

    def validate(self, data):
        self.context['_identified_racer'] = self._get_racer_instance_from_input_data(data)

        racer_for_validation = None
        if self.instance:
            racer_for_validation = self.context.get('_identified_racer', self.instance.racer)
        else:
            racer_for_validation = self.context.get('_identified_racer')

        if racer_for_validation:
            run_type = data.get('run_type', self.instance.run_type if self.instance else None)
            run_identifier = data.get('run_identifier', self.instance.run_identifier if self.instance else None)

            if run_type is not None and run_identifier is not None:
                queryset = RaceRun.objects.filter(
                    racer=racer_for_validation,
                    run_type=run_type,
                    run_identifier=run_identifier
                )
                if self.instance:
                    queryset = queryset.exclude(pk=self.instance.pk)

                if queryset.exists():
                    raise serializers.ValidationError(
                        _("A race run with this racer, run type, and run identifier already exists."),
                        code='unique'
                    )
        elif not self.instance:
            raise serializers.ValidationError(
                _("A racer must be identified via 'racer' (PK), 'racer_id', or 'racer_start_number'.")
            )

        disqualified_value = data.get('disqualified', self.instance.disqualified if self.instance else False)
        time_value = data.get('time_in_seconds', self.instance.time_in_seconds if self.instance else None)

        if disqualified_value and time_value is not None:
            if 'time_in_seconds' in data or not self.instance:
                raise serializers.ValidationError({
                    'time_in_seconds': _("A disqualified run cannot have a time. Set time to null or remove it.")
                })
            elif 'disqualified' in data and 'time_in_seconds' not in data:
                data['time_in_seconds'] = None

        return data

    def create(self, validated_data):
        racer_instance = self.context.get('_identified_racer')
        if not racer_instance:
            raise serializers.ValidationError(_("Internal error: Racer could not be determined for creation."))

        validated_data.pop('racer_id', None)
        validated_data.pop('racer_start_number', None)

        validated_data['racer'] = racer_instance
        return super().create(validated_data)

    def update(self, instance, validated_data):
        identified_racer_for_update = self.context.get('_identified_racer')
        if identified_racer_for_update:
            validated_data['racer'] = identified_racer_for_update
        elif 'racer' in self.initial_data and self.initial_data['racer'] is None:
            raise serializers.ValidationError({'racer': _("Cannot disassociate a racer from an existing RaceRun.")})

        if validated_data.get('disqualified', instance.disqualified) and 'time_in_seconds' not in validated_data:
            validated_data['time_in_seconds'] = None

        validated_data.pop('racer_id', None)
        validated_data.pop('racer_start_number', None)

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RaceRunSerializer(instance, context=self.context).data
