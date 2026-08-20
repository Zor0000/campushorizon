from django.core.management.base import BaseCommand

from events.scraper.config import COLLECTORS
from events.scraper.validator import validate_all, validate_source
from events.scraper.archive import list_runs


class Command(BaseCommand):
    help = 'Check extraction health and suggest bdata scraper heal commands'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source', type=str, default=None,
            help='Check a single source (devpost, luma, mlh, devfolio)',
        )
        parser.add_argument(
            '--run-id', type=str, default=None,
            help='Check a specific archived run (default: latest)',
        )
        parser.add_argument(
            '--exit-code', action='store_true',
            help='Exit with code 1 if any ERROR issues found (CI-ready)',
        )

    def handle(self, *args, **options):
        source = options['source']
        run_id = options['run_id']
        exit_code = options['exit_code']

        if source:
            if source not in COLLECTORS:
                self.stderr.write(f'Unknown source: {source}. Choose from: {", ".join(COLLECTORS)}')
                return
            results = {source: validate_source(source, run_id=run_id)}
        else:
            results = validate_all(run_id=run_id)

        total_errors = 0
        total_warnings = 0

        for src, issues in results.items():
            collector_id = COLLECTORS.get(src, {}).get('collector_id', '?')
            target_url = COLLECTORS.get(src, {}).get('target_url', '?')

            if not issues:
                self.stdout.write(f'  [{src.upper()}] OK')
                continue

            errors = [i for i in issues if i.severity == 'error']
            warnings = [i for i in issues if i.severity == 'warning']
            total_errors += len(errors)
            total_warnings += len(warnings)

            self.stdout.write(f'\n  [{src.upper()}]  Collector: {collector_id}')
            self.stdout.write(f'  Target:    {target_url}')
            self.stdout.write(f'  Issues:    {len(errors)} error(s), {len(warnings)} warning(s)')

            for issue in issues:
                self.stdout.write(str(issue))

        self.stdout.write('')
        if total_errors > 0:
            self.stdout.write(self.style.ERROR(
                f'FAIL: {total_errors} error(s), {total_warnings} warning(s)'
            ))
            if exit_code:
                self.exit_code = 1
        elif total_warnings > 0:
            self.stdout.write(self.style.WARNING(
                f'WARN: {total_warnings} warning(s) — review recommended'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('ALL OK — all sources healthy'))
