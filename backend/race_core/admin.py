from django.contrib import admin
from .models import Team, Racer


class RacerInline(admin.TabularInline):
    model = Racer
    extra = 1
    fields = ('first_name', 'last_name', 'date_of_birth')
    readonly_fields = ('get_age',)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'racer_count')
    search_fields = ('name',)
    inlines = [RacerInline]

    def racer_count(self, obj):
        return obj.racers.count() # Verwendet related_name 'racers'
    racer_count.short_description = "Number of Racers"


@admin.register(Racer)
class RacerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'date_of_birth', 'team', 'display_age')
    list_filter = ('team', 'date_of_birth')
    search_fields = ('first_name', 'last_name', 'team__name')
    autocomplete_fields = ['team']
    fieldsets = (
        (None, {
            'fields': ('first_name', 'last_name', 'date_of_birth', 'display_age')
        }),
        ('Team Information', {
            'fields': ('team',)
        }),
    )
    readonly_fields = ('display_age',)

    def display_age(self, obj):
        from datetime import date
        if obj.date_of_birth:
            today = date.today()
            age = today.year - obj.date_of_birth.year - \
                  ((today.month, today.day) < (obj.date_of_birth.month, obj.date_of_birth.day))
            return age
        return None
    display_age.short_description = "Age"
