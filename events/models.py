from django.db import models
from django.utils import timezone


class Source(models.TextChoices):
    DEVPOST = 'devpost', 'Devpost'
    LUMA = 'luma', 'Luma'
    MLH = 'mlh', 'MLH'
    DEVFOLIO = 'devfolio', 'Devfolio'


class Event(models.Model):
    title = models.CharField(max_length=500)
    source = models.CharField(max_length=20, choices=Source.choices, db_index=True)
    url = models.URLField(unique=True, max_length=1000)
    deadline = models.DateTimeField(null=True, blank=True, db_index=True)
    prizes = models.CharField(max_length=500, blank=True, default='')
    tags = models.JSONField(default=list, blank=True)
    is_online = models.BooleanField(null=True, blank=True)
    location = models.CharField(max_length=300, blank=True, default='')
    event_type = models.CharField(max_length=100, blank=True, default='')
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['deadline']

    def __str__(self):
        return f"[{self.source}] {self.title}"


class EventSnapshot(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='snapshots')
    captured_at = models.DateTimeField(default=timezone.now, db_index=True)
    title = models.CharField(max_length=500)
    deadline = models.DateTimeField(null=True, blank=True)
    prizes = models.CharField(max_length=500, blank=True, default='')
    tags = models.JSONField(default=list, blank=True)
    is_online = models.BooleanField(null=True, blank=True)
    location = models.CharField(max_length=300, blank=True, default='')

    class Meta:
        ordering = ['-captured_at']

    def __str__(self):
        return f"{self.event.title} @ {self.captured_at}"
