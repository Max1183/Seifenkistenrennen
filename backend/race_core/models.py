from django.db import models


class Team(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Racer(models.Model):
    name = models.CharField(max_length=255)
    team = models.ForeignKey(Team, related_name='racers', on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class RaceRun(models.Model):
    team = models.ForeignKey(Team, related_name='runs', on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    is_valid = models.BooleanField(default=True)

    def __str__(self):
        return f"Run for {self.team.name} at {self.start_time}"
