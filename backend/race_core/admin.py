from django.contrib import admin
from .models import Team, Racer, RaceRun, Soapbox


class RacerInline(admin.TabularInline):
    model = Racer
    extra = 1
    fields = ('first_name', 'last_name')


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'racer_count')
    search_fields = ('name',)
    inlines = [RacerInline]

    def racer_count(self, obj):
        return obj.racers.count()
    racer_count.short_description = "Number of Racers"


@admin.register(Soapbox)
class SoapboxAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


class RaceRunInline(admin.TabularInline): # Oder StackedInline
    model = RaceRun
    fields = ('run_type', 'run_identifier', 'time_in_seconds', 'disqualified', 'notes')
    extra = 1


@admin.register(Racer)
class RacerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'start_number', 'soapbox_class', 'team', 'best_time_display')
    list_filter = ('soapbox_class', 'team')
    search_fields = ('first_name', 'last_name', 'team__name', 'start_number')
    autocomplete_fields = ['team']
    inlines = [RaceRunInline] # Erlaube das direkte Hinzufügen von Rennläufen zum Racer
    fieldsets = (
        (None, {
            'fields': ('first_name', 'last_name', 'soapbox', 'start_number', 'soapbox_class')
        }),
        ('Team Affiliation', {
            'fields': ('team',)
        }),
    )
    readonly_fields = ('best_time_display',)

    def best_time_display(self, obj):
        time_val = obj.best_time_seconds
        return f"{time_val}s" if time_val is not None else "N/A"
    best_time_display.short_description = "Best Time"


@admin.register(RaceRun)
class RaceRunAdmin(admin.ModelAdmin):
    list_display = ('racer_link', 'run_type_display', 'run_identifier', 'time_in_seconds', 'disqualified')
    list_filter = ('run_type', 'disqualified', 'racer__team', 'racer__soapbox_class')
    search_fields = ('racer__first_name', 'racer__last_name', 'racer__start_number', 'notes')
    autocomplete_fields = ['racer']
    list_select_related = ('racer', 'racer__team')

    fieldsets = (
        (None, {
            'fields': ('racer', 'run_type', 'run_identifier')
        }),
        ('Time and Status', {
            'fields': ('time_in_seconds', 'disqualified')
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    def run_type_display(self, obj):
        return obj.get_run_type_display()
    run_type_display.short_description = "Run Type"
    run_type_display.admin_order_field = 'run_type'

    def racer_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        link = reverse("admin:race_core_racer_change", args=[obj.racer.id])
        return format_html('<a href="{}">{}</a>', link, obj.racer.full_name)
    racer_link.short_description = "Racer"
    racer_link.admin_order_field = 'racer'
