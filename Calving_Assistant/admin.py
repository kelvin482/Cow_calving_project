from django.contrib import admin
from .models import CalvingEvent


@admin.register(CalvingEvent)
class CalvingEventAdmin(admin.ModelAdmin):
    list_display = ('cow_id', 'observed_at')
