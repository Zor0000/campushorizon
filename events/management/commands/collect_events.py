import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone

from events.models import Event, EventSnapshot
from events.scraper.normalizer import NORMALIZERS, _load_sample
from events.scraper.config import COLLECTORS
from events.scraper.archive import new_run_id, save_raw_run, write_manifest, purge_old_runs

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
TMP_DIR = BASE_DIR / 'tmp'


class Command(BaseCommand):
    help = 'Collect events from all scrapers and upsert into DB'

    def add_arguments(self, parser):
        parser.add_argument(
            '--offline', action='store_true', default=True,
            help='Read from tmp/*.json instead of triggering Bright Data API',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would be imported without writing to DB',
        )
        parser.add_argument(
            '--keep-runs', type=int, default=20,
            help='Number of raw runs to retain (default: 20)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        keep_runs = options['keep_runs']

        run_id = new_run_id()
        raw_counts = {}

        for source in COLLECTORS:
            raw = _load_sample(source)
            if not dry_run:
                save_raw_run(run_id, source, raw)
            raw_counts[source] = len(raw) if isinstance(raw, list) else 1

        if not dry_run:
            write_manifest(run_id, raw_counts, mode='offline')
            removed = purge_old_runs(keep=keep_runs)
            self.stdout.write(f'Archived raw data to raw/{run_id}')
            if removed:
                self.stdout.write(f'Purged {removed} old run(s), keeping last {keep_runs}')

        results = {}
        for source, normalizer in NORMALIZERS.items():
            raw = _load_sample(source)
            results[source] = normalizer(raw)

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

        self.stdout.write(self.style.SUCCESS(
            f'\nDone! Created: {created_count}, Updated: {updated_count}, Skipped: {skipped_count}'
        ))
