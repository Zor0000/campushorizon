from django.contrib import admin
from events.models import Event, EventSnapshot


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'source', 'deadline', 'prizes', 'is_online')
    list_filter = ('source', 'is_online')
    search_fields = ('title', 'url', 'location')


@admin.register(EventSnapshot)
class EventSnapshotAdmin(admin.ModelAdmin):
    list_display = ('event', 'captured_at')
    list_filter = ('captured_at',)
