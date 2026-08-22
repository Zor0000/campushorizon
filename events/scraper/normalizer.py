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
    'sept': 9,
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


def _nearest_future_year(month, day, now=None):
    """Return the year that makes (month, day) the nearest occurrence not in the past."""
    now = now or datetime.now(timezone.utc)
    year = now.year
    try:
        candidate = datetime(year, month, day, tzinfo=timezone.utc)
    except ValueError:
        return year
    if candidate < now:
        year += 1
    return year


def _parse_dmy(text):
    """Parse day-first dates like '28 Aug 2026' or '4 Sept 2026'."""
    if not text:
        return None
    match = re.match(r'^(\d{1,2})\s+(\w+),?\s*(\d{4})$', str(text).strip(), re.IGNORECASE)
    if not match:
        return None
    day, month_str, yr = match.groups()
    month = MONTH_MAP.get(month_str.lower())
    if not month or not 1 <= int(day) <= 31:
        return None
    return datetime(int(yr), month, int(day), tzinfo=timezone.utc)


def _parse_mlh_date(text):
    """Parse MLH date like 'JULY 17' or 'JULY 17, 2026'. Month/day only → nearest future year."""
    if not text:
        return None
    match = re.match(
        r'(\w+)\s+(\d{1,2})(?:,?\s*(\d{4}))?',
        text.strip(), re.IGNORECASE
    )
    if not match:
        return None
    month_str, day, yr = match.groups()
    month = MONTH_MAP.get(month_str.lower())
    if not month:
        return None
    day = int(day)
    if yr:
        return datetime(int(yr), month, day, tzinfo=timezone.utc)
    return datetime(_nearest_future_year(month, day), month, day, tzinfo=timezone.utc)


def _parse_luma_date(text):
    """Parse Luma dates: ISO '2026-09-14', '26/9' (D/M) or '26/9/26'. Missing year → nearest future."""
    if not text:
        return None
    text = str(text).strip()
    iso = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})', text)
    if iso:
        yr, month, day = (int(g) for g in iso.groups())
        if 1 <= month <= 12 and 1 <= day <= 31:
            return datetime(yr, month, day, tzinfo=timezone.utc)
        return None
    match = re.match(r'^(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?$', text)
    if match:
        day, month, yr = match.groups()
        day, month = int(day), int(month)
        if not 1 <= month <= 12 or not 1 <= day <= 31:
            return None
        if yr:
            yr = int(yr)
            if yr < 100:
                yr += 2000
        else:
            yr = _nearest_future_year(month, day)
        return datetime(yr, month, day, tzinfo=timezone.utc)
    return _parse_date_range(text)


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


def _clean_devpost_prize(raw_prize):
    """Clean Devpost API prize string like '$<span data-currency-value>740,000</span>' → '$740,000 USD'."""
    if not raw_prize:
        return ''
    cleaned = re.sub(r'<[^>]+>', '', str(raw_prize)).strip()
    if not cleaned or cleaned == '$0':
        return ''
    if cleaned.startswith('$'):
        return f'{cleaned} USD'
    if cleaned.startswith('₹'):
        return f'{cleaned} INR'
    return cleaned


def normalize_devpost(raw_data):
    """Devpost returns either a flat list of hackathons or a list of pages with 'hackathons' keys.
    Handles both Bright Data scraper format and direct API format.
    """
    events = []
    seen = set()

    if raw_data and isinstance(raw_data[0], dict) and 'hackathons' in raw_data[0]:
        records = [h for page in raw_data for h in page.get('hackathons', [])]
    else:
        records = raw_data

    for h in records:
        url = h.get('hackathon_url', h.get('url', '')).split('?')[0]
        if not url or url in seen:
            continue
        seen.add(url)

        deadline = _parse_date_range(h.get('submission_deadline', h.get('submission_period_dates', '')))
        prize = _format_prize(h.get('prize_amount')) or _clean_devpost_prize(h.get('prize_amount'))

        tags = h.get('tags', [])
        if not tags and 'themes' in h:
            tags = [t.get('name', '') for t in h.get('themes', []) if t.get('name')]

        loc = h.get('location_type', '')
        if not loc and 'displayed_location' in h:
            dl = h['displayed_location']
            loc = dl.get('location', '') if isinstance(dl, dict) else str(dl)

        is_online = None
        if loc:
            is_online = 'online' in loc.lower()

        event_type = h.get('_query_type', '')
        if not event_type:
            event_type = 'online' if is_online else 'in-person-india'

        events.append({
            'title': h.get('title', '').strip(),
            'source': Source.DEVPOST,
            'url': url,
            'deadline': deadline,
            'prizes': prize,
            'tags': tags,
            'is_online': is_online,
            'location': loc,
            'event_type': event_type,
        })
    return events


def normalize_luma(raw_data):
    """Luma returns a flat list of event dicts."""
    events = []
    seen = set()

    for e in raw_data:
        url = e.get('event_url', '').split('?')[0].rstrip('/')
        if not url or url in seen:
            continue
        seen.add(url)

        raw_date = e.get('event_date', '')
        deadline = _parse_luma_date(raw_date)

        is_online = None
        for key in ('is_online', 'online', 'event_type', 'event_format', 'format', 'location_type'):
            value = e.get(key)
            if value is None:
                continue
            if isinstance(value, bool):
                is_online = value
                break
            text = str(value).strip().lower()
            if text:
                if 'online' in text or 'virtual' in text:
                    is_online = True
                elif 'person' in text or 'venue' in text or 'offline' in text or 'hybrid' in text:
                    is_online = False
                break

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
            deadline = (
                _parse_date_range(end) or _parse_mlh_date(end)
                or _parse_date_range(start) or _parse_mlh_date(start)
            )

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


def _first(raw, *keys):
    for key in keys:
        value = raw.get(key)
        if value:
            return value
    return ''


def _parse_bool_flag(value):
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if not text:
        return None
    if 'online' in text or 'virtual' in text:
        return True
    if 'person' in text or 'venue' in text or 'offline' in text:
        return False
    return None


def _title_from_slug(url):
    """Derive a readable title from a lablab event slug like /ai-hackathons/ibm-bob-2-hackathon."""
    slug = url.rstrip('/').rsplit('/', 1)[-1]
    slug = re.sub(r'^\d+[-_]', '', slug)
    words = re.split(r'[-_]+', slug)
    return ' '.join(w.capitalize() for w in words if w)


def normalize_lablab(raw_data):
    """LabLab returns a flat list of hackathon dicts."""
    events = []
    seen = set()

    for h in raw_data:
        url = str(_first(h, 'event_url', 'url', 'product_page_url')).split('?')[0].rstrip('/')
        if not url or url in seen:
            continue
        seen.add(url)

        raw_deadline = _first(h, 'submission_deadline', 'deadline', 'end_date')
        deadline = (
            _parse_date_range(raw_deadline)
            or _parse_dmy(raw_deadline)
            or _parse_luma_date(str(raw_deadline))
        )
        prize = _format_prize(h.get('prize_amount')) or str(_first(h, 'prize', 'prize_pool'))

        fmt = str(_first(h, 'format', 'event_format', 'location_type', 'mode'))
        is_online = _parse_bool_flag(fmt)
        location = str(_first(h, 'location', 'venue'))
        tags = h.get('tech_tags') or h.get('tags') or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',') if t.strip()]
        company = h.get('hosting_company') or h.get('company') or h.get('host')
        if company and str(company) not in tags:
            tags = tags + [str(company)]

        title = str(_first(h, 'title', 'event_title', 'hackathon_name')).strip()
        if not title:
            title = _title_from_slug(url)

        events.append({
            'title': title,
            'source': Source.LABLAB,
            'url': url,
            'deadline': deadline,
            'prizes': prize,
            'tags': tags,
            'is_online': is_online,
            'location': location,
        })
    return events


def normalize_meetup(raw_data):
    """Meetup returns records that may nest event dicts under an 'events' key."""
    events = []
    seen = set()

    flat = []
    for record in raw_data:
        nested = record.get('events') if isinstance(record, dict) else None
        if isinstance(nested, list) and nested:
            for e in nested:
                e.setdefault('event_url', record.get('product_page_url') or record.get('event_url', ''))
                flat.append(e)
        elif isinstance(record, dict):
            flat.append(record)

    for e in flat:
        url = str(_first(e, 'event_url', 'url')).split('?')[0].rstrip('/')
        if not url or url in seen:
            continue
        seen.add(url)

        raw_date = _first(e, 'start_date_time', 'start_date', 'date', 'event_date', 'datetime')
        deadline = _parse_luma_date(str(raw_date)) or _parse_dmy(str(raw_date)) or _parse_date_range(str(raw_date))

        group = e.get('group_name') or e.get('group')
        title = str(_first(e, 'title', 'event_title', 'name')).strip()
        if group and str(group).lower() not in title.lower():
            title = f'{title} · {group}'

        venue = str(_first(e, 'venue', 'location'))
        is_online = True if venue.strip().lower() == 'online' else _parse_bool_flag(
            _first(e, 'is_online', 'online', 'event_type', 'format', 'location_type')
        )

        events.append({
            'title': title,
            'source': Source.MEETUP,
            'url': url,
            'deadline': deadline,
            'prizes': '',
            'tags': [],
            'is_online': is_online,
            'location': '' if venue.strip().lower() == 'online' else venue,
        })
    return events


def normalize_devpost_online(raw_data):
    return normalize_devpost(raw_data)


def normalize_devpost_india(raw_data):
    return normalize_devpost(raw_data)


NORMALIZERS = {
    'devpost': normalize_devpost,
    'devpost_online': normalize_devpost_online,
    'devpost_india': normalize_devpost_india,
    'luma': normalize_luma,
    'mlh': normalize_mlh,
    'devfolio': normalize_devfolio,
    'lablab': normalize_lablab,
    'meetup': normalize_meetup,
}


def normalize_all(offline=True):
    """Load sample files and normalize all sources. Returns dict of source → list of event dicts."""
    results = {}
    for source, normalizer in NORMALIZERS.items():
        raw = _load_sample(source)
        results[source] = normalizer(raw)
    return results
