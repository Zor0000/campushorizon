from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from events.models import Event, EventSnapshot
from events.scraper import client
from events.scraper.normalizer import NORMALIZERS, _load_sample
from events.scraper.config import COLLECTORS
from events.scraper.archive import new_run_id, save_raw_run, write_manifest, purge_old_runs

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
TMP_DIR = BASE_DIR / 'tmp'


class Command(BaseCommand):
    help = 'Collect events from all scrapers and upsert into DB'

    def add_arguments(self, parser):
        parser.add_argument(
            '--online', action='store_true', default=False,
            help='Trigger live Bright Data collectors and fetch fresh data (requires BRIGHT_DATA_API_TOKEN)',
        )
        parser.add_argument(
            '--offline', action='store_true', default=False,
            help='Read from tmp/*.json instead of triggering Bright Data API (default)',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would be imported without writing to DB',
        )
        parser.add_argument(
            '--keep-runs', type=int, default=20,
            help='Number of raw runs to retain (default: 20)',
        )
        parser.add_argument(
            '--source', type=str, default=None,
            help='Collect a single source only, e.g. devpost (default: all sources)',
        )
        parser.add_argument(
            '--poll-timeout', type=int, default=25,
            help='Minutes to wait per collector before failing (online mode, default: 25)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        keep_runs = options['keep_runs']
        online = options['online']
        poll_timeout = options['poll_timeout'] * 60
        only_source = options['source']

        if only_source and only_source not in COLLECTORS:
            self.stderr.write(f'Unknown source: {only_source}. Choose from: {", ".join(COLLECTORS)}')
            return
        sources = [only_source] if only_source else list(COLLECTORS)

        if online and options['offline']:
            self.stderr.write('Use either --online or --offline, not both.')
            return

        run_id = new_run_id()
        raw_by_source = {}

        if online:
            client.load_env()
            self.stdout.write('Triggering live collectors...')
            failures = []
            for source in sources:
                try:
                    raw = client.collect_source(source, timeout=poll_timeout)
                    raw_by_source[source] = raw
                    count = len(raw) if isinstance(raw, list) else 1
                    self.stdout.write(f'  {source}: {count} record(s)')
                    if not dry_run:
                        save_raw_run(run_id, source, raw)
                except (client.BDAPIError, TimeoutError) as exc:
                    failures.append((source, exc))
                    self.stderr.write(f'  {source}: FAILED — {exc}')
            if not dry_run:
                write_manifest(run_id, {
                    s: len(r) if isinstance(r, list) else 1
                    for s, r in raw_by_source.items()
                }, mode='online')
                removed = purge_old_runs(keep=keep_runs)
                self.stdout.write(f'Archived raw data to raw/{run_id}')
                if removed:
                    self.stdout.write(f'Purged {removed} old run(s), keeping last {keep_runs}')
            for source, exc in failures:
                self.stderr.write(self.style.ERROR(f'{source}: {exc}'))
            if failures:
                raise CommandError(
                    f'{len(failures)} source(s) failed to collect: {", ".join(s for s, _ in failures)}',
                    returncode=1,
                )
        else:
            for source in sources:
                raw_by_source[source] = _load_sample(source)
            if not dry_run:
                for source, raw in raw_by_source.items():
                    save_raw_run(run_id, source, raw)
                write_manifest(run_id, {
                    s: len(r) if isinstance(r, list) else 1
                    for s, r in raw_by_source.items()
                }, mode='offline')
                removed = purge_old_runs(keep=keep_runs)
                self.stdout.write(f'Archived raw data to raw/{run_id}')
                if removed:
                    self.stdout.write(f'Purged {removed} old run(s), keeping last {keep_runs}')

        results = {}
        for source, normalizer in NORMALIZERS.items():
            if source in raw_by_source:
                results[source] = normalizer(raw_by_source[source])

        created, updated, skipped = self._import_events(results, dry_run)

        self.stdout.write(self.style.SUCCESS(
            f'\nDone! Created: {created}, Updated: {updated}, Skipped: {skipped}'
        ))

    def _import_events(self, results, dry_run):
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for source, events in results.items():
            self.stdout.write(f'\n--- {source.upper()} ({len(events)} events) ---')

            for data in events:
                url = data.pop('url')
                event_type = data.pop('event_type', '')

                existing = Event.objects.filter(url=url).first()

                if existing:
                    changed = False
                    for key, value in data.items():
                        if key == 'tags':
                            if set(existing.tags or []) != set(value or []):
                                changed = True
                        elif getattr(existing, key) != value:
                            changed = True

                    if changed:
                        if not dry_run:
                            for key, value in data.items():
                                setattr(existing, key, value)
                            existing.save()
                            EventSnapshot.objects.create(
                                event=existing,
                                title=existing.title,
                                deadline=existing.deadline,
                                prizes=existing.prizes,
                                tags=existing.tags,
                                is_online=existing.is_online,
                                location=existing.location,
                            )
                        updated_count += 1
                        self.stdout.write(f'  UPDATE: {data["title"]}')
                    else:
                        skipped_count += 1
                else:
                    if not dry_run:
                        event = Event.objects.create(
                            title=data['title'],
                            source=data['source'],
                            url=url,
                            deadline=data.get('deadline'),
                            prizes=data.get('prizes', ''),
                            tags=data.get('tags', []),
                            is_online=data.get('is_online'),
                            location=data.get('location', ''),
                            event_type=event_type,
                        )
                        EventSnapshot.objects.create(
                            event=event,
                            title=event.title,
                            deadline=event.deadline,
                            prizes=event.prizes,
                            tags=event.tags,
                            is_online=event.is_online,
                            location=event.location,
                        )
                    created_count += 1
                    self.stdout.write(f'  NEW:    {data["title"]}')

        return created_count, updated_count, skipped_count