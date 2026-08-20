from django.core.management.base import BaseCommand, CommandError

from events.scraper import client
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
        parser.add_argument(
            '--auto-heal', action='store_true',
            help='Trigger Bright Data self-healing (refactor_template) for sources with ERROR issues',
        )

    def handle(self, *args, **options):
        source = options['source']
        run_id = options['run_id']
        exit_code = options['exit_code']
        auto_heal = options['auto_heal']

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

            if auto_heal and errors:
                self._trigger_heal(src, collector_id, target_url, errors[0])

        self.stdout.write('')
        if total_errors > 0:
            self.stdout.write(self.style.ERROR(
                f'FAIL: {total_errors} error(s), {total_warnings} warning(s)'
            ))
            if exit_code:
                raise CommandError(
                    f'{total_errors} error(s) found in health check',
                    returncode=1,
                )
        elif total_warnings > 0:
            self.stdout.write(self.style.WARNING(
                f'WARN: {total_warnings} warning(s) — review recommended'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('ALL OK — all sources healthy'))

    def _trigger_heal(self, source, collector_id, target_url, issue):
        prompt = (
            f'{issue.message}. The target page is {target_url}. '
            'Refactor the scraper template so extraction works again.'
        )
        try:
            client.load_env()
            client.heal_collector(collector_id, prompt)
            self.stdout.write(self.style.SUCCESS(
                f'\n  [HEAL] Auto-heal triggered for {source} ({collector_id})\n'
                f'         Approve with: npx -p @brightdata/cli bdata scraper approve {collector_id}'
            ))
        except client.BDAPIError as exc:
            self.stderr.write(self.style.ERROR(f'\n  [HEAL] Auto-heal failed for {source}: {exc}'))
