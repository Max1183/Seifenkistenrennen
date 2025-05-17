from datetime import date

from django.db import models
from django.utils.translation import gettext_lazy as _


class Team(models.Model):
    name = models.CharField(
        _("Team Name"),
        max_length=100,
        unique=True,
        help_text=_("The official name of the team.")
    )

    class Meta:
        verbose_name = _("Team")
        verbose_name_plural = _("Teams")
        ordering = ['name']

    def __str__(self):
        return self.name


class Racer(models.Model):
    first_name = models.CharField(_("First Name"), max_length=50)
    last_name = models.CharField(_("Last Name"), max_length=50)
    date_of_birth = models.DateField(
        _("Date of Birth"),
        help_text=_("Used to determine age category if applicable.")
    )

    team = models.ForeignKey(
        Team,
        related_name='racers',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Team")
    )

    start_number = models.CharField(_("Start Number"), max_length=10, blank=True, null=True, unique=True)

    class Meta:
        verbose_name = _("Racer")
        verbose_name_plural = _("Racers")
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_age(self):
        today = date.today()
        return today.year - self.date_of_birth.year - \
               ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
