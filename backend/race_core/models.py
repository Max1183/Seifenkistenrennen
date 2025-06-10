from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Team(models.Model):
    name = models.CharField(
        _("Team Name"),
        max_length=100,
        unique=True,
        help_text=_("The official name of the team.")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Team")
        verbose_name_plural = _("Teams")
        ordering = ['name']

    def __str__(self):
        return self.name


class Racer(models.Model):
    first_name = models.CharField(_("First Name"), max_length=50)
    last_name = models.CharField(_("Last Name"), max_length=50)

    class SoapboxClass(models.TextChoices):
        LUFTREIFEN_JUNIOR = 'LJ', _('Luftreifen Junior')
        LUFTREIFEN_SENIOR = 'LS', _('Luftreifen Senior')
        HARTREIFEN_JUNIOR = 'HJ', _('Hartreifen Junior')
        HARTREIFEN_SENIOR = 'HS', _('Hartreifen Senior')
        X_KLASSE = 'XK', _('X-Klasse')
        VETERANEN = 'VT', _('Veteranen')
        UNKNOWN = 'UN', _('Unknown')

    soapbox_class = models.CharField(
        _("Soapbox Class"),
        max_length=2,
        choices=SoapboxClass.choices,
        default=SoapboxClass.UNKNOWN,
        help_text=_("The class the racer is competing in."),
    )

    team = models.ForeignKey(
        Team,
        related_name='racers',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Team")
    )

    start_number = models.CharField(
        _("Start Number"),
        max_length=10,
        blank=True,
        null=True,
        unique=True
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Racer")
        verbose_name_plural = _("Racers")
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def best_time_seconds(self):
        valid_runs = self.races.filter(disqualified=False, time_in_seconds__isnull=False)
        if valid_runs.exists():
            return valid_runs.order_by('time_in_seconds').first().time_in_seconds
        return None


class RaceRun(models.Model):
    racer = models.ForeignKey(
        Racer,
        related_name='races',
        on_delete=models.CASCADE,
        verbose_name=_("Racer")
    )

    time_in_seconds = models.DecimalField(
        _("Time (seconds)"),
        max_digits=6,
        decimal_places=3,
        blank=True,
        null=True,
        help_text=_("Time taken for this run in seconds (e.g., 45.123).")
    )
    disqualified = models.BooleanField(_("Disqualified"), default=False)
    notes = models.TextField(_("Notes"), blank=True, null=True)

    run_identifier = models.PositiveSmallIntegerField(
        _("Run Identifier"),
        default=1,
        help_text=_("Identifier for the run (e.g., 1 for first attempt, 2 for second of a specific type).")
    )

    class RaceRunType(models.TextChoices):
        PRACTICE = 'PR', _('Practice')
        HEAT_1 = 'H1', _('Heat 1')
        HEAT_2 = 'H2', _('Heat 2')

    run_type = models.CharField(
        _("Run Type"),
        max_length=2,
        choices=RaceRunType.choices,
        default=RaceRunType.PRACTICE,
        help_text=_("Type of race run (e.g., Practice, Heat 1, Heat 2).")
    )
    recorded_at = models.DateTimeField(default=timezone.now, verbose_name=_("Recorded At"))

    class Meta:
        verbose_name = _("Race Run")
        verbose_name_plural = _("Race Runs")
        unique_together = ('racer', 'run_type', 'run_identifier')
        ordering = ['racer__last_name', 'racer__first_name', 'run_type', 'run_identifier']

    def __str__(self):
        status = "DQ" if self.disqualified else (f"{self.time_in_seconds}s" if self.time_in_seconds is not None else "N/A")
        return f"{self.racer.full_name} - {self.get_run_type_display()} Run {self.run_identifier} - {status}"
