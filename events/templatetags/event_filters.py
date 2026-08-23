from datetime import timedelta

from django import template
from django.utils import timezone

register = template.Library()

RECENT_WINDOW_HOURS = 36

SOURCE_COLORS = {
    'devpost': {'bg': 'bg-indigo-500/20', 'text': 'text-indigo-300', 'border': 'border-indigo-500/30', 'label': 'Devpost'},
    'luma': {'bg': 'bg-sky-500/20', 'text': 'text-sky-300', 'border': 'border-sky-500/30', 'label': 'Luma'},
    'mlh': {'bg': 'bg-emerald-500/20', 'text': 'text-emerald-300', 'border': 'border-emerald-500/30', 'label': 'MLH'},
    'devfolio': {'bg': 'bg-purple-500/20', 'text': 'text-purple-300', 'border': 'border-purple-500/30', 'label': 'Devfolio'},
    'lablab': {'bg': 'bg-fuchsia-500/20', 'text': 'text-fuchsia-300', 'border': 'border-fuchsia-500/30', 'label': 'LabLab'},
    'meetup': {'bg': 'bg-rose-500/20', 'text': 'text-rose-300', 'border': 'border-rose-500/30', 'label': 'Meetup'},
}


@register.filter
def source_color(source):
    return SOURCE_COLORS.get(source, {'bg': 'bg-white/10', 'text': 'text-white/60', 'border': 'border-white/20', 'label': source})


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def days_left(deadline):
    if not deadline:
        return None
    now = timezone.now()
    delta = deadline - now
    days = delta.days
    if days < 0:
        return 'ended'
    if days == 0:
        return 'today'
    return days


@register.filter
def deadline_badge_class(deadline):
    days = days_left(deadline)
    if days == 'ended':
        return 'bg-white/5 text-white/40 border-white/10'
    if days == 'today':
        return 'bg-red-500/20 text-red-400 border-red-500/30'
    if isinstance(days, int) and days <= 7:
        return 'bg-amber-500/20 text-amber-400 border-amber-500/30'
    return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'


@register.filter
def deadline_badge_text(event):
    deadline = event.deadline
    days = days_left(deadline)
    if event.source == 'mlh':
        if days == 'ended':
            return 'Finished'
        if days == 'today':
            return 'Starts today'
        if isinstance(days, int):
            return f'Starts in {days}d'
        return 'No date'
    if days == 'ended':
        return 'Ended'
    if days == 'today':
        return 'Ends today'
    if isinstance(days, int):
        return f'Ends in {days}d'
    return 'No date'


@register.filter
def format_prize(prizes):
    return prizes or None


@register.filter
def stagger_delay(index):
    return f'{min(index * 0.04, 0.4):.2f}s'


@register.filter
def is_recent(event):
    if not getattr(event, 'created_at', None):
        return False
    cutoff = timezone.now() - timedelta(hours=RECENT_WINDOW_HOURS)
    return event.created_at >= cutoff