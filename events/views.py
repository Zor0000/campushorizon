from datetime import timedelta

from django.core.paginator import Paginator
from django.db.models import Q, Count, Max
from django.shortcuts import render
from django.utils import timezone

from events.models import Event, Source

PAGE_SIZE = 24

HACKATHON_SOURCES = [Source.DEVPOST, Source.MLH, Source.DEVFOLIO, Source.LABLAB]
TECH_EVENT_SOURCES = [Source.LUMA, Source.MEETUP]

# Which filter groups apply per category and their copy.
# 'source' is always rendered. 'ended' is available everywhere.
FILTER_CONFIG = {
    'hackathons': {
        'groups': ['online', 'prizes', 'soon', 'ended'],
        'soon_label': 'Ending soon',
    },
    'tech-events': {
        'groups': ['soon', 'ended'],
        'soon_label': 'Starting soon',
    },
}


def _remove_url(request, key, value=None):
    params = request.GET.copy()
    params.pop('page', None)
    if value is None:
        params.pop(key, None)
    else:
        values = params.getlist(key)
        params.pop(key, None)
        for v in values:
            if v != value:
                params.appendlist(key, v)
    qs = params.urlencode()
    return f'{request.path}?{qs}' if qs else request.path


def _page_url(request, page_number):
    params = request.GET.copy()
    params['page'] = page_number
    qs = params.urlencode()
    return f'{request.path}?{qs}'


def _get_feed(request, sources, category):
    config = FILTER_CONFIG[category]
    groups = config['groups']

    queryset = Event.objects.filter(source__in=sources)
    now = timezone.now()

    q = request.GET.get('q', '').strip()
    if q:
        queryset = queryset.filter(
            Q(title__icontains=q) | Q(location__icontains=q)
        )

    source_values = [s.value for s in sources]
    selected_sources = [v for v in request.GET.getlist('source') if v in source_values]
    if selected_sources:
        queryset = queryset.filter(source__in=selected_sources)

    if not request.GET.get('ended'):
        queryset = queryset.filter(
            Q(deadline__isnull=True) | Q(deadline__gte=now)
        )

    if 'online' in groups and request.GET.get('online'):
        queryset = queryset.filter(is_online=True)

    if 'prizes' in groups and request.GET.get('prizes'):
        queryset = queryset.exclude(prizes='')

    if 'soon' in groups and request.GET.get('soon'):
        soon_cutoff = now + timedelta(days=7)
        queryset = queryset.filter(
            Q(deadline__isnull=False) & Q(deadline__lte=soon_cutoff)
        )

    sort = request.GET.get('sort', 'deadline')

    dated = queryset.filter(deadline__isnull=False)
    undated = queryset.filter(deadline__isnull=True)

    if sort == 'newest':
        dated = dated.order_by('-created_at')
        undated = undated.order_by('-created_at')
    else:
        dated = dated.order_by('deadline')
        undated = undated.order_by('-created_at')

    source_counts = dict(
        Event.objects.filter(source__in=sources)
        .values_list('source')
        .annotate(c=Count('id'))
        .values_list('source', 'c')
    )

    source_choices = dict(Source.choices)
    active_filters = []
    if q:
        active_filters.append({
            'label': f'Search “{q}”',
            'remove_url': _remove_url(request, 'q'),
        })
    for v in selected_sources:
        active_filters.append({
            'label': source_choices.get(v, v),
            'remove_url': _remove_url(request, 'source', v),
        })
    if 'online' in groups and request.GET.get('online'):
        active_filters.append({
            'label': 'Online only',
            'remove_url': _remove_url(request, 'online'),
        })
    if 'prizes' in groups and request.GET.get('prizes'):
        active_filters.append({
            'label': 'Has prizes',
            'remove_url': _remove_url(request, 'prizes'),
        })
    if 'soon' in groups and request.GET.get('soon'):
        active_filters.append({
            'label': config['soon_label'],
            'remove_url': _remove_url(request, 'soon'),
        })
    if request.GET.get('ended'):
        active_filters.append({
            'label': 'Include ended',
            'remove_url': _remove_url(request, 'ended'),
        })

    return dated, undated, source_counts, active_filters, config


def landing(request):
    now = timezone.now()
    week_ahead = now + timedelta(days=7)

    hackathon_count = Event.objects.filter(source__in=HACKATHON_SOURCES).count()
    tech_event_count = Event.objects.filter(source__in=TECH_EVENT_SOURCES).count()

    ending_soon_qs = Event.objects.filter(
        source__in=HACKATHON_SOURCES,
        deadline__gte=now,
        deadline__lte=week_ahead,
    )

    ending_week_count = ending_soon_qs.count()
    ending_soon = list(ending_soon_qs.order_by('deadline')[:8])

    last_refreshed = Event.objects.aggregate(t=Max('last_updated'))['t']

    return render(request, 'events/landing.html', {
        'hackathon_count': hackathon_count,
        'tech_event_count': tech_event_count,
        'total_count': hackathon_count + tech_event_count,
        'ending_week_count': ending_week_count,
        'ending_soon': ending_soon,
        'last_refreshed': last_refreshed,
        'source_count': len(Source.values),
    })


def hackathons(request):
    dated, undated, source_counts, active_filters, config = _get_feed(
        request, HACKATHON_SOURCES, 'hackathons'
    )
    selected_sources = [
        s for s in request.GET.getlist('source')
        if s in [x.value for x in HACKATHON_SOURCES]
    ]

    paginator = Paginator(dated, PAGE_SIZE)
    page_num = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_num)
    remaining_count = max(0, paginator.count - (page_obj.number * PAGE_SIZE))
    next_page_url = _page_url(request, page_obj.next_page_number()) if page_obj.has_next() else None

    return render(request, 'events/feed.html', {
        'events': page_obj.object_list,
        'page_obj': page_obj,
        'remaining_count': remaining_count,
        'next_page_url': next_page_url,
        'undated_events': undated,
        'total_count': paginator.count + undated.count(),
        'source_counts': source_counts,
        'active_filters': active_filters,
        'filter_config': config,
        'page_title': 'Hackathons',
        'sources': HACKATHON_SOURCES,
        'category': 'hackathons',
        'selected_sources': selected_sources,
    })


def tech_events(request):
    dated, undated, source_counts, active_filters, config = _get_feed(
        request, TECH_EVENT_SOURCES, 'tech-events'
    )
    selected_sources = [
        s for s in request.GET.getlist('source')
        if s in [x.value for x in TECH_EVENT_SOURCES]
    ]

    paginator = Paginator(dated, PAGE_SIZE)
    page_num = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_num)
    remaining_count = max(0, paginator.count - (page_obj.number * PAGE_SIZE))
    next_page_url = _page_url(request, page_obj.next_page_number()) if page_obj.has_next() else None

    return render(request, 'events/feed.html', {
        'events': page_obj.object_list,
        'page_obj': page_obj,
        'remaining_count': remaining_count,
        'next_page_url': next_page_url,
        'undated_events': undated,
        'total_count': paginator.count + undated.count(),
        'source_counts': source_counts,
        'active_filters': active_filters,
        'filter_config': config,
        'page_title': 'Tech Events',
        'sources': TECH_EVENT_SOURCES,
        'category': 'tech-events',
        'selected_sources': selected_sources,
    })
