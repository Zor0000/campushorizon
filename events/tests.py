import json
import os
import shutil
from pathlib import Path
from unittest import mock

from django.test import TestCase

from events.models import Event, Source
from events.scraper import client
from events.scraper.archive import (
    new_run_id, save_raw_run, load_raw, load_latest_raw,
    list_runs, write_manifest, purge_old_runs,
)
from events.scraper.validator import validate_source, validate_all, Issue
from events.scraper.config import COLLECTORS


class FakeResp:
    def __init__(self, status_code, payload=None, text=''):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        return self._payload


class ClientTest(TestCase):
    def setUp(self):
        os.environ['BRIGHT_DATA_API_TOKEN'] = 'test-token'

    def tearDown(self):
        os.environ.pop('BRIGHT_DATA_API_TOKEN', None)

    @mock.patch('events.scraper.client.requests.request')
    def test_trigger_collector(self, req):
        req.return_value = FakeResp(200, {'collection_id': 'j_abc'})
        collection_id = client.trigger_collector('c_devpost', 'https://devpost.com/hackathons')
        self.assertEqual(collection_id, 'j_abc')
        args, kwargs = req.call_args
        self.assertEqual(kwargs['params']['collector'], 'c_devpost')
        self.assertEqual(kwargs['json'], [{'url': 'https://devpost.com/hackathons'}])
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer test-token')

    @mock.patch('events.scraper.client.requests.request')
    def test_trigger_retries_on_5xx(self, req):
        req.side_effect = [
            FakeResp(503, {}, 'oops'),
            FakeResp(200, {'collection_id': 'j_retry'}),
        ]
        with mock.patch('events.scraper.client.time.sleep'):
            collection_id = client.trigger_collector('c_devpost', 'https://devpost.com/hackathons')
        self.assertEqual(collection_id, 'j_retry')
        self.assertEqual(req.call_count, 2)

    @mock.patch('events.scraper.client.requests.request')
    def test_trigger_422_raises_with_fix(self, req):
        req.return_value = FakeResp(422, {}, 'schema mismatch')
        with self.assertRaises(client.BDAPIError) as ctx:
            client.trigger_collector('c_devpost', 'https://devpost.com/hackathons')
        self.assertEqual(ctx.exception.status, 422)
        self.assertIsNotNone(ctx.exception.fix)

    @mock.patch('events.scraper.client.requests.request')
    def test_fetch_not_ready_raises(self, req):
        req.return_value = FakeResp(202, {'status': 'building', 'message': 'try again'})
        with self.assertRaises(client.CollectionNotReady):
            client.fetch_dataset('j_abc')

    @mock.patch('events.scraper.client.requests.request')
    def test_fetch_ready_returns_records(self, req):
        records = [{'title': 'X', 'url': 'https://x.dev'}]
        req.return_value = FakeResp(200, records)
        self.assertEqual(client.fetch_dataset('j_abc'), records)

    @mock.patch('events.scraper.client.requests.request')
    def test_collect_source_polls_until_ready(self, req):
        req.side_effect = [
            FakeResp(200, {'collection_id': 'j_poll'}),
            FakeResp(202, {'status': 'building'}),
            FakeResp(202, {'status': 'building'}),
            FakeResp(200, [{'title': 'Y'}]),
        ]
        with mock.patch('events.scraper.client.time.sleep'):
            records = client.collect_source('devpost', poll_interval=0)
        self.assertEqual(records, [{'title': 'Y'}])
        self.assertEqual(req.call_count, 4)

    @mock.patch('events.scraper.client.requests.request')
    def test_collect_source_times_out(self, req):
        req.side_effect = [
            FakeResp(200, {'collection_id': 'j_abc'}),
            FakeResp(202, {'status': 'building'}),
        ]
        mono_values = iter([100.0, 200.0])
        with mock.patch('events.scraper.client.time.monotonic', side_effect=lambda: next(mono_values)):
            with self.assertRaises(TimeoutError):
                client.collect_source('devpost', timeout=0.001, poll_interval=0)

    @mock.patch('events.scraper.client.requests.request')
    def test_heal_collector(self, req):
        req.return_value = FakeResp(200, {})
        ok = client.heal_collector('c_devpost', 'Fix selector issues')
        self.assertTrue(ok)
        args, kwargs = req.call_args
        self.assertIn('/dca/collectors/c_devpost/refactor_template', args[1])
        self.assertEqual(kwargs['json']['prompt'], 'Fix selector issues')

    def test_missing_token_raises(self):
        os.environ.pop('BRIGHT_DATA_API_TOKEN', None)
        with self.assertRaises(client.BDAPIError) as ctx:
            client.get_api_token()
        self.assertEqual(ctx.exception.status, 401)


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

    def test_online_collect_uses_live_data(self):
        from django.core.management import call_command
        from events.scraper.normalizer import _load_sample
        with mock.patch(
            'events.scraper.client.collect_source',
            side_effect=lambda source, **kw: _load_sample(source),
        ):
            call_command('collect_events', '--online')
        self.assertGreater(Event.objects.count(), 0)

    def test_online_collect_reports_failures(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError
        with mock.patch(
            'events.scraper.client.collect_source',
            side_effect=client.BDAPIError(404, 'collector not found'),
        ):
            with self.assertRaises(CommandError) as ctx:
                call_command('collect_events', '--online')
        self.assertEqual(ctx.exception.returncode, 1)


class HealCheckTest(TestCase):
    def test_auto_heal_triggers_for_broken_source(self):
        from django.core.management import call_command
        with mock.patch(
            'events.scraper.validator.load_latest_raw',
            side_effect=FileNotFoundError,
        ):
            with mock.patch('events.scraper.validator._load_sample', return_value=[]):
                with mock.patch('events.scraper.client.heal_collector', return_value=True) as heal:
                    call_command('heal_check', '--source', 'devpost', '--auto-heal')
        heal.assert_called_once()
        args, _kwargs = heal.call_args
        self.assertEqual(args[0], COLLECTORS['devpost']['collector_id'])
        self.assertIn('devpost', args[1])

    def test_auto_heal_skips_healthy_sources(self):
        from django.core.management import call_command
        with mock.patch('events.scraper.client.heal_collector', return_value=True) as heal:
            call_command('heal_check', '--source', 'devfolio', '--auto-heal')
        heal.assert_not_called()

    def test_exit_code_raises_on_errors(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError
        with mock.patch(
            'events.scraper.validator.load_latest_raw',
            side_effect=FileNotFoundError,
        ):
            with mock.patch('events.scraper.validator._load_sample', return_value=[]):
                with self.assertRaises(CommandError) as ctx:
                    call_command('heal_check', '--source', 'devpost', '--exit-code')
        self.assertEqual(ctx.exception.returncode, 1)


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
