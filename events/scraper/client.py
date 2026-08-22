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


def collect_devpost_api(source):
    """Collect Devpost hackathons via their public JSON API (no auth required).
    Returns a list of records compatible with the normalizer.
    """
    info = COLLECTORS[source]
    api_url = info['api_url']
    all_hackathons = []

    for params_key in ('api_params', 'api_params_upcoming'):
        params = info.get(params_key, {})
        page = 1
        while True:
            resp = requests.get(api_url, params={**params, 'page': page}, timeout=30)
            if resp.status_code != 200:
                raise BDAPIError(resp.status_code, f'Devpost API error: {resp.text[:200]}')
            data = resp.json()
            hackathons = data.get('hackathons', [])
            if not hackathons:
                break
            for h in hackathons:
                h['_query_type'] = params.get('challenge_type', 'online')
            all_hackathons.extend(hackathons)
            meta = data.get('meta', {})
            total = meta.get('total_count', 0)
            per_page = meta.get('per_page', 9)
            if page * per_page >= total:
                break
            page += 1
            time.sleep(0.5)

    return [{'hackathons': all_hackathons, 'product_page_url': api_url}]


DEVFOLIO_GQL_FIELDS = (
    'name slug tagline starts_at ends_at is_online '
    'city country state location participants_count type uuid '
    'private verified featured fellowship edition edition_name desc '
    'apply_mode team_min team_size devfolio_official uri '
    'settings { reg_starts_at reg_ends_at site primary_color }'
)


def collect_devfolio_api(source):
    """Collect Devfolio hackathons via their public GraphQL API (no auth).
    Uses raw GraphQL where/order_by strings from config (Hasura `now` built-in).
    Paginates with offset (20 per page) and returns flat list of records.
    """
    info = COLLECTORS[source]
    api_url = info['api_url']
    where = info['gql_where']
    order_by = info['gql_order_by']

    all_hackathons = []
    offset = 0

    while True:
        query = (
            f'{{ hackathons('
            f'where: {where}, '
            f'limit: 20, '
            f'offset: {offset}, '
            f'order_by: {order_by}'
            f') {{ {DEVFOLIO_GQL_FIELDS} }} }}'
        )
        resp = requests.post(
            api_url,
            json={'query': query},
            headers={'Content-Type': 'application/json'},
            timeout=30,
        )
        if resp.status_code != 200:
            raise BDAPIError(resp.status_code, f'Devfolio API error: {resp.text[:200]}')
        data = resp.json()
        if 'errors' in data:
            raise BDAPIError(422, f'Devfolio GraphQL error: {data["errors"][0]["message"]}')
        hackathons = data.get('data', {}).get('hackathons', [])
        if not hackathons:
            break
        all_hackathons.extend(hackathons)
        if len(hackathons) < 20:
            break
        offset += 20
        time.sleep(0.3)

    return all_hackathons


def collect_source(source, token=None, timeout=1500, poll_interval=30):
    if source not in COLLECTORS:
        raise ValueError(f'Unknown source: {source}')
    info = COLLECTORS[source]

    if 'api_url' in info:
        if source.startswith('devfolio_'):
            return collect_devfolio_api(source)
        return collect_devpost_api(source)

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