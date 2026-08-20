import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from events.scraper.config import COLLECTORS

API_BASE = 'https://api.brightdata.com'
RETRY_STATUSES = {500, 502, 503, 504}
MAX_RETRIES = 3
BACKOFF_SECONDS = [1, 2, 4]


def load_env():
    env_path = Path(__file__).resolve().parent.parent.parent / '.env'
    load_dotenv(env_path)


class BDAPIError(Exception):
    def __init__(self, status, message, fix=None):
        super().__init__(message)
        self.status = status
        self.fix = fix

    def __str__(self):
        text = f'Bright Data API error {self.status}: {self.args[0]}'
        if self.fix:
            text += f' — {self.fix}'
        return text


class CollectionNotReady(Exception):
    pass


def get_api_token():
    token = os.environ.get('BRIGHT_DATA_API_TOKEN', '').strip()
    if not token:
        raise BDAPIError(
            401,
            'BRIGHT_DATA_API_TOKEN is not set',
            'add it to .env (see .env.example) or export it in the environment',
        )
    return token


def _request(method, path, token, params=None, json=None):
    url = f'{API_BASE}{path}'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.request(method, url, headers=headers, params=params, json=json, timeout=60)
        except requests.RequestException as exc:
            last_error = BDAPIError(0, f'network failure: {exc}')
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_SECONDS[attempt])
                continue
            raise last_error

        if resp.status_code in RETRY_STATUSES and attempt < MAX_RETRIES:
            time.sleep(BACKOFF_SECONDS[attempt])
            continue
        if resp.status_code == 401:
            raise BDAPIError(401, 'token missing, malformed or revoked',
                             're-copy from Account Settings → API Tokens')
        if resp.status_code == 404:
            raise BDAPIError(404, f'{method} {path} not found',
                             'check the collector/collection id')
        if resp.status_code == 422:
            raise BDAPIError(422, 'request body does not match the collector input schema',
                             'confirm field names against the collector Inputs tab')
        if resp.status_code >= 400:
            raise BDAPIError(resp.status_code, resp.text[:300])
        return resp
    raise last_error


def trigger_collector(collector_id, url, token=None):
    token = token or get_api_token()
    resp = _request(
        'POST', '/dca/trigger', token,
        params={'collector': collector_id, 'queue_next': 1},
        json=[{'url': url}],
    )
    data = resp.json()
    collection_id = data.get('collection_id')
    if not collection_id:
        raise BDAPIError(200, f'unexpected trigger response: {data}')
    return collection_id


def fetch_dataset(collection_id, token=None):
    token = token or get_api_token()
    resp = _request('GET', '/dca/dataset', token, params={'id': collection_id})
    if resp.status_code == 202:
        raise CollectionNotReady(resp.json().get('message', 'dataset still building'))
    return resp.json()


def collect_source(source, token=None, timeout=1500, poll_interval=30):
    if source not in COLLECTORS:
        raise ValueError(f'Unknown source: {source}')
    info = COLLECTORS[source]
    collection_id = trigger_collector(info['collector_id'], info['target_url'], token=token)

    deadline = time.monotonic() + timeout
    while True:
        try:
            return fetch_dataset(collection_id, token=token)
        except CollectionNotReady:
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f'{source}: collection {collection_id} not ready after {timeout}s'
                )
            time.sleep(poll_interval)


def heal_collector(collector_id, prompt, token=None):
    token = token or get_api_token()
    if len(prompt) > 1000:
        prompt = prompt[:997] + '...'
    resp = _request(
        'POST', f'/dca/collectors/{collector_id}/refactor_template', token,
        json={'prompt': prompt},
    )
    return resp.status_code == 200