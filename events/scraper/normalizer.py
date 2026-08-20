import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from events.models import Event, Source

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TMP_DIR = BASE_DIR / 'tmp'

MONTH_MAP = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4,
    'may': 5, 'june': 6, 'july': 7, 'august': 8,
    'september': 9, 'october': 10, 'november': 11, 'december': 12,
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
    'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}


def _load_sample(source):
    from events.scraper.config import COLLECTORS
    filename = COLLECTORS[source]['sample_file']
    with open(TMP_DIR / filename) as f:
        return json.load(f)


def _parse_date_range(text, year=2026):
    """Parse 'Jul 31 - Oct 01, 2026' → end datetime. Parse 'Aug 8, 2026' → that date."""
    if not text:
        return None
    text = text.strip().rstrip(',').strip()
    text_lower = text.lower()

    # 'Sep 25 - 26, 2026' → end = Sep 26
    match = re.match(
        r'(\w+)\s+(\d{1,2})\s*[-–]\s*(\d{1,2}),?\s*(\d{4})',
        text, re.IGNORECASE
    )
    if match:
        month_str, _start_day, end_day, yr = match.groups()
        month = MONTH_MAP.get(month_str.lower())
        if month:
            return datetime(int(yr), month, int(end_day), tzinfo=timezone.utc)

    # 'Jul 31 - Oct 01, 2026' → end = Oct 01
    match = re.match(
        r'(\w+)\s+(\d{1,2})\s*[-–]\s*(\w+)\s+(\d{1,2}),?\s*(\d{4})',
        text, re.IGNORECASE
    )
    if match:
        _m1, _d1, month_str, end_day, yr = match.groups()
        month = MONTH_MAP.get(month_str.lower())
        if month:
            return datetime(int(yr), month, int(end_day), tzinfo=timezone.utc)

    # 'Aug 8, 2026'
    match = re.match(r'(\w+)\s+(\d{1,2}),?\s*(\d{4})', text, re.IGNORECASE)
    if match:
        month_str, day, yr = match.groups()
        month = MONTH_MAP.get(month_str.lower())
        if month:
            return datetime(int(yr), month, int(day), tzinfo=timezone.utc)

    return None


def _parse_mlh_date(text):
    """Parse MLH date like 'JULY 17' → datetime."""
    if not text:
        return None
    match = re.match(r'(\w+)\s+(\d{1,2})', text.strip(), re.IGNORECASE)
    if match:
        month_str, day = match.groups()
        month = MONTH_MAP.get(month_str.lower())
        if month:
            return datetime(2026, month, int(day), tzinfo=timezone.utc)
    return None


def _format_prize(prize):
    """Convert {'value': 15318, 'currency': 'USD', 'symbol': '$'} → '$15,318 USD'."""
    if not prize or not isinstance(prize, dict):
        return ''
    value = prize.get('value')
    symbol = prize.get('symbol', '$')
    currency = prize.get('currency', 'USD')
    if value is None:
        return ''
    try:
        return f"{symbol}{int(value):,} {currency}"
    except (ValueError, TypeError):
        return ''


def normalize_devpost(raw_data):
    """Devpost returns a list of pages, each with 'hackathons' key."""
    events = []
    seen = set()

    for page in raw_data:
        hackathons = page.get('hackathons', [])
        for h in hackathons:
            url = h.get('hackathon_url', '').split('?')[0]
            if not url or url in seen:
                continue
            seen.add(url)

            deadline = _parse_date_range(h.get('submission_deadline', ''))
            prize = _format_prize(h.get('prize_amount'))
            is_online = None
            loc = h.get('location_type', '')
            if loc:
                is_online = 'online' in loc.lower()

            events.append({
                'title': h.get('title', '').strip(),
                'source': Source.DEVPOST,
                'url': url,
                'deadline': deadline,
                'prizes': prize,
                'tags': h.get('tags', []),
                'is_online': is_online,
                'location': loc,
            })
    return events


def normalize_luma(raw_data):
    """Luma returns a flat list of event dicts."""
    events = []
    seen = set()

    for e in raw_data:
        url = e.get('event_url', '').rstrip('/')
        if not url or url in seen:
            continue
        seen.add(url)

        raw_date = e.get('event_date', '')
        deadline = None
        if raw_date:
            deadline = _parse_date_range(raw_date)

        events.append({
            'title': e.get('event_title', '').strip(),
            'source': Source.LUMA,
            'url': url,
            'deadline': deadline,
            'prizes': '',
            'tags': [],
            'is_online': None,
            'location': e.get('location', ''),
        })
    return events


def normalize_mlh(raw_data):
    """MLH returns list of pages, each with 'events' key. Skip entries without names."""
    events = []
    seen = set()

    for page in raw_data:
        for e in page.get('events', []):
            url = e.get('event_url', '').split('?')[0]
            name = e.get('event_name', '').strip()
            if not url or url in seen:
                continue
            if not name:
                continue
            seen.add(url)

            start = e.get('start_date', '')
            end = e.get('end_date', '')
            deadline = _parse_mlh_date(start) or _parse_mlh_date(end)

            event_type = e.get('event_type', '')
            location = e.get('location', '')
            is_online = None
            if 'digital' in event_type.lower() or 'online' in location.lower():
                is_online = True
            elif 'in-person' in event_type.lower():
                is_online = False

            events.append({
                'title': name,
                'source': Source.MLH,
                'url': url,
                'deadline': deadline,
                'prizes': '',
                'tags': [],
                'is_online': is_online,
                'location': location,
                'event_type': event_type,
            })
    return events


def normalize_devfolio(raw_data):
    """Devfolio returns a flat list of hackathon dicts."""
    events = []
    seen = set()

    for h in raw_data:
        url = h.get('product_page_url', '')
        if not url or url in seen:
            continue
        seen.add(url)

        deadline = _parse_date_range(h.get('submission_deadline', ''))
        prize = _format_prize(h.get('prize_amount'))

        events.append({
            'title': h.get('hackathon_name', '').strip(),
            'source': Source.DEVFOLIO,
            'url': url,
            'deadline': deadline,
            'prizes': prize,
            'tags': [],
            'is_online': None,
            'location': '',
        })
    return events


NORMALIZERS = {
    'devpost': normalize_devpost,
    'luma': normalize_luma,
    'mlh': normalize_mlh,
    'devfolio': normalize_devfolio,
}


def normalize_all(offline=True):
    """Load sample files and normalize all sources. Returns dict of source → list of event dicts."""
    results = {}
    for source, normalizer in NORMALIZERS.items():
        raw = _load_sample(source)
        results[source] = normalizer(raw)
    return results
