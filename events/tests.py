import json
import shutil
from pathlib import Path
from unittest import mock

from django.test import TestCase

from events.models import Event, Source
from events.scraper.archive import (
    new_run_id, save_raw_run, load_raw, load_latest_raw,
    list_runs, write_manifest, purge_old_runs,
)
from events.scraper.validator import validate_source, validate_all, Issue
from events.scraper.config import COLLECTORS


class ArchiveTest(TestCase):
    def setUp(self):
        self.test_dir = Path(__file__).resolve().parent / '_test_archive'

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def _patch_raw_dir(self):
        return mock.patch('events.scraper.archive.RAW_DIR', self.test_dir)

    def test_save_and_load_roundtrip(self):
        test_data = [{'hackathon_name': 'Test', 'product_page_url': 'https://test.dev'}]
        with self._patch_raw_dir():
            run_id = '20260820_120000'
            save_raw_run(run_id, 'devfolio', test_data)
            loaded = load_raw(run_id, 'devfolio')
            self.assertEqual(loaded, test_data)

    def test_load_nonexistent_raises(self):
        with self._patch_raw_dir():
            with self.assertRaises(FileNotFoundError):
                load_raw('20990101_000000', 'devfolio')

    def test_list_runs(self):
        with self._patch_raw_dir():
            save_raw_run('20260820_120000', 'devfolio', [])
            save_raw_run('20260820_130000', 'devfolio', [])
            runs = list_runs()
            self.assertEqual(runs, ['20260820_120000', '20260820_130000'])

    def test_purge_old_runs(self):
        with self._patch_raw_dir():
            for i in range(5):
                save_raw_run(f'2026082{i}_120000', 'devfolio', [])
            removed = purge_old_runs(keep=3)
            self.assertEqual(removed, 2)
            self.assertEqual(len(list_runs()), 3)

    def test_write_manifest(self):
        with self._patch_raw_dir():
            write_manifest('20260820_120000', {'devfolio': 28})
            manifest_path = self.test_dir / '20260820_120000' / 'manifest.json'
            with open(manifest_path) as f:
                manifest = json.load(f)
            self.assertEqual(manifest['run_id'], '20260820_120000')
            self.assertEqual(manifest['source_counts'], {'devfolio': 28})

    def test_new_run_id_format(self):
        rid = new_run_id()
        self.assertEqual(len(rid), 15)
        self.assertIn('_', rid)


GOOD_DEVFOLIO = [
    {'hackathon_name': 'Good', 'product_page_url': 'https://good.dev', 'submission_deadline': 'Sep 25, 2026'},
]

# Non-empty list but empty URL causes normalizer to skip all records → R1
EMPTY_URL_DEVFOLIO = [{'hackathon_name': 'X', 'product_page_url': ''}]

# URL exists but title missing → R3
MISSING_TITLE_DEVFOLIO = [{'hackathon_name': '', 'product_page_url': 'https://a.dev'}] * 10


class ValidatorTest(TestCase):
    def setUp(self):
        Event.objects.create(
            title='Existing', source=Source.DEVFOLIO, url='https://exists.dev'
        )

    def test_r0_empty_data(self):
        with mock.patch('events.scraper.validator._load_sample', return_value=[]):
            with mock.patch('events.scraper.validator.load_latest_raw', side_effect=FileNotFoundError):
                issues = validate_source('devfolio')
        self.assertTrue(any(i.rule == 'R0' for i in issues),
                        f"Expected R0, got: {[i.rule for i in issues]}")

    def test_r1_zero_records(self):
        with mock.patch('events.scraper.validator.load_raw', return_value=EMPTY_URL_DEVFOLIO):
            issues = validate_source('devfolio', run_id='test')
        rules = [i.rule for i in issues]
        self.assertIn('R1', rules, f"Expected R1, got: {rules}")

    def test_r3_missing_fields(self):
        with mock.patch('events.scraper.validator.load_raw', return_value=MISSING_TITLE_DEVFOLIO):
            issues = validate_source('devfolio', run_id='test')
        rules = [i.rule for i in issues]
        self.assertIn('R3', rules, f"Expected R3, got: {rules}")

    def test_healthy_data_no_errors(self):
        with mock.patch('events.scraper.validator.load_raw', return_value=GOOD_DEVFOLIO):
            issues = validate_source('devfolio', run_id='test')
        errors = [i for i in issues if i.severity == 'error']
        self.assertEqual(len(errors), 0)

    def test_validate_all_uses_latest(self):
        with mock.patch('events.scraper.validator.load_latest_raw', return_value=('run', GOOD_DEVFOLIO)):
            results = validate_all()
        self.assertIn('devfolio', results)
        self.assertIn('devpost', results)


class CollectEventsTest(TestCase):
    def test_offline_collect(self):
        from django.core.management import call_command
        call_command('collect_events', '--offline')
        self.assertGreater(Event.objects.count(), 0)

    def test_dry_run_no_write(self):
        from django.core.management import call_command
        initial_count = Event.objects.count()
        call_command('collect_events', '--offline', '--dry-run')
        self.assertEqual(Event.objects.count(), initial_count)


class ViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        from django.core.management import call_command
        call_command('collect_events', '--offline')

    def test_landing_200(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)

    def test_hackathons_200(self):
        resp = self.client.get('/hackathons/')
        self.assertEqual(resp.status_code, 200)

    def test_tech_events_200(self):
        resp = self.client.get('/tech-events/')
        self.assertEqual(resp.status_code, 200)

    def test_hackathons_has_source_badges(self):
        resp = self.client.get('/hackathons/')
        content = resp.content.decode()
        self.assertIn('Devpost', content)
        self.assertIn('MLH', content)
        self.assertIn('Devfolio', content)

    def test_tech_events_has_luma(self):
        resp = self.client.get('/tech-events/')
        content = resp.content.decode()
        self.assertIn('Luma', content)

    def test_filter_online(self):
        resp = self.client.get('/hackathons/?online=1')
        self.assertEqual(resp.status_code, 200)

    def test_filter_prizes(self):
        resp = self.client.get('/hackathons/?prizes=1')
        self.assertEqual(resp.status_code, 200)

    def test_filter_source(self):
        resp = self.client.get('/hackathons/?source=devpost')
        self.assertEqual(resp.status_code, 200)

    def test_filter_source_only_returns_that_source(self):
        resp = self.client.get('/hackathons/?source=devpost')
        content = resp.content.decode()
        self.assertIn('RevenueCat', content)
        self.assertNotIn('Global Hack Week', content)

    def test_filter_soon_returns_events(self):
        resp = self.client.get('/hackathons/?soon=1')
        self.assertEqual(resp.status_code, 200)

    def test_filter_online_returns_online_events(self):
        resp = self.client.get('/hackathons/?online=1')
        content = resp.content.decode()
        self.assertIn('Online', content)

    def test_source_radio_uses_value_not_enum(self):
        resp = self.client.get('/hackathons/')
        content = resp.content.decode()
        self.assertIn('value="devpost"', content)
        self.assertIn('value="mlh"', content)
        self.assertIn('value="devfolio"', content)

    def test_filter_search(self):
        resp = self.client.get('/hackathons/?q=hack')
        self.assertEqual(resp.status_code, 200)

    def test_hackathons_show_prize_and_online_filters(self):
        resp = self.client.get('/hackathons/')
        content = resp.content.decode()
        self.assertIn('Has prizes', content)
        self.assertIn('Online only', content)

    def test_tech_events_hide_prize_and_online_filters(self):
        resp = self.client.get('/tech-events/')
        content = resp.content.decode()
        self.assertNotIn('Has prizes', content)
        self.assertNotIn('Online only', content)

    def test_tech_events_no_prize_rows(self):
        resp = self.client.get('/tech-events/')
        content = resp.content.decode()
        self.assertNotIn('prize', content.lower())

    def test_landing_shows_counts(self):
        resp = self.client.get('/')
        content = resp.content.decode()
        self.assertIn('events', content.lower())
