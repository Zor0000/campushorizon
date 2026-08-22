from events.scraper.config import COLLECTORS, SOURCE_CATEGORIES
from events.scraper.normalizer import NORMALIZERS, _load_sample
from events.scraper.archive import load_latest_raw, load_raw
from events.models import Event, Source

DEADLINE_SOURCES = {'devpost', 'devfolio', 'mlh', 'lablab'}
REQUIRED_FIELDS = {'title', 'url'}


class Issue:
    def __init__(self, severity, rule, message, heal_command=None):
        self.severity = severity
        self.rule = rule
        self.message = message
        self.heal_command = heal_command

    def __str__(self):
        icon = 'ERROR' if self.severity == 'error' else 'WARNING'
        parts = f'  [{icon}] {self.rule}: {self.message}'
        if self.heal_command:
            parts += f'\n         Fix: {self.heal_command}'
        return parts


def _check_rule_r0(source, raw_data):
    if not raw_data:
        target_url = COLLECTORS[source].get('target_url') or COLLECTORS[source].get('api_url', '')
        return [Issue('error', 'R0', f'{source}: raw data is empty',
                      f'bdata scraper create {target_url} "..."')]
    return []


def _check_rule_r1(source, raw_data):
    normalizer = NORMALIZERS[source]
    normalized = normalizer(raw_data)
    if len(normalized) == 0:
        collector_id = COLLECTORS[source].get('collector_id')
        if collector_id:
            fix = f'npx -p @brightdata/cli bdata scraper heal {collector_id} "extraction returned 0 records - likely layout change"'
        else:
            fix = f'Check API endpoint or sample file for {source}'
        return [Issue('error', 'R1', f'{source}: 0 records extracted from valid data', fix)]
    return []


def _check_rule_r2(source, normalized_count):
    try:
        db_count = Event.objects.filter(source=source).count()
    except Exception:
        return []

    if db_count == 0:
        return []

    ratio = normalized_count / db_count
    if ratio < 0.5:
        return [Issue('warning', 'R2',
                      f'{source}: extracted {normalized_count} events, only {ratio:.0%} of DB count ({db_count})')]
    return []


def _check_rule_r3(source, raw_data):
    normalizer = NORMALIZERS[source]
    normalized = normalizer(raw_data)
    if not normalized:
        return []

    missing_title = sum(1 for e in normalized if not e.get('title'))
    missing_url = sum(1 for e in normalized if not e.get('url'))
    total = len(normalized)
    title_pct = missing_title / total
    url_pct = missing_url / total

    issues = []
    if title_pct > 0.1:
        issues.append(Issue('warning', 'R3', f'{source}: {missing_title}/{total} records missing title'))
    if url_pct > 0.1:
        issues.append(Issue('warning', 'R3', f'{source}: {missing_url}/{total} records missing url'))
    return issues


def _check_rule_r4(source, raw_data):
    if source not in DEADLINE_SOURCES:
        return []

    normalizer = NORMALIZERS[source]
    normalized = normalizer(raw_data)
    if not normalized:
        return []

    with_deadline = sum(1 for e in normalized if e.get('deadline'))
    ratio = with_deadline / len(normalized)

    try:
        db_with_deadline = Event.objects.filter(source=source).exclude(deadline__isnull=True).count()
        db_total = Event.objects.filter(source=source).count()
        if db_total > 0:
            db_ratio = db_with_deadline / db_total
            if ratio < db_ratio * 0.5:
                return [Issue('warning', 'R4',
                              f'{source}: deadline coverage dropped to {ratio:.0%} (was {db_ratio:.0%} in DB)')]
    except Exception:
        pass

    return []


def validate_source(source, run_id=None):
    if run_id:
        raw = load_raw(run_id, source)
    else:
        try:
            _, raw = load_latest_raw(source)
        except FileNotFoundError:
            raw = _load_sample(source)

    issues = []
    issues.extend(_check_rule_r0(source, raw))
    if issues:
        return issues

    normalizer = NORMALIZERS[source]
    normalized = normalizer(raw)

    issues.extend(_check_rule_r1(source, raw))
    issues.extend(_check_rule_r2(source, len(normalized)))
    issues.extend(_check_rule_r3(source, raw))
    issues.extend(_check_rule_r4(source, raw))

    return issues


def validate_all(run_id=None):
    results = {}
    for source in COLLECTORS:
        try:
            issues = validate_source(source, run_id=run_id)
            results[source] = issues
        except FileNotFoundError as e:
            results[source] = [Issue('error', 'R0', str(e))]
    return results
