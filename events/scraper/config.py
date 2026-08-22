COLLECTORS = {
    'devpost': {
        'collector_id': 'c_msz1ehqzhdlpeq7og',
        'name': 'devpost-hackathons',
        'target_url': 'https://devpost.com/hackathons',
        'sample_file': 'devpost_sample.json',
    },
    'devpost_online': {
        'api_url': 'https://devpost.com/api/hackathons',
        'api_params': {'challenge_type': 'online', 'status': 'open'},
        'api_params_upcoming': {'challenge_type': 'online', 'status': 'upcoming'},
        'name': 'devpost-online-hackathons',
        'sample_file': 'devpost_online_sample.json',
    },
    'devpost_india': {
        'api_url': 'https://devpost.com/api/hackathons',
        'api_params': {'challenge_type': 'in-person', 'search': 'india', 'status': 'open'},
        'api_params_upcoming': {'challenge_type': 'in-person', 'search': 'india', 'status': 'upcoming'},
        'name': 'devpost-india-hackathons',
        'sample_file': 'devpost_india_sample.json',
    },
    'luma': {
        'collector_id': 'c_mt09dzgd2mai4o8bhu',
        'name': 'luma-tech-categories',
        'target_url': 'https://luma.com/tech',
        'sample_file': 'luma_tech_cat_final.json',
    },
    'mlh': {
        'collector_id': 'c_mt0hfqqi1q7jk1sdbo',
        'name': 'mlh-hackathons',
        'target_url': 'https://mlh.io/events',
        'sample_file': 'mlh_sample.json',
    },
    'devfolio': {
        'collector_id': 'c_mt0y94lp18i9rcuhhv',
        'name': 'devfolio-hackathons-v2',
        'target_url': 'https://devfolio.co/hackathons',
        'sample_file': 'devfolio_sample.json',
    },
    'devfolio_open': {
        'api_url': 'https://api.devfolio.co/v1/graphql',
        'gql_where': '{ _and: [{ private: { _eq: false } }, { settings: { reg_starts_at: { _lte: now } } }, { settings: { reg_ends_at: { _gte: now } } }] }',
        'gql_order_by': '{ settings: { reg_ends_at: asc } }',
        'name': 'devfolio-open',
        'sample_file': 'devfolio_open_sample.json',
    },
    'devfolio_upcoming': {
        'api_url': 'https://api.devfolio.co/v1/graphql',
        'gql_where': '{ _and: [{ private: { _eq: false } }, { starts_at: { _gte: now } }] }',
        'gql_order_by': '{ starts_at: asc }',
        'name': 'devfolio-upcoming',
        'sample_file': 'devfolio_upcoming_sample.json',
    },
    'lablab': {
        'collector_id': 'c_mt2pm82fb4ta19gqe',
        'name': 'lablab-ai-hackathons',
        'target_url': 'https://lablab.ai/ai-hackathons',
        'sample_file': 'lablab_sample.json',
    },
    'meetup': {
        'collector_id': 'c_mt2qwd9216p13lefvg',
        'name': 'meetup-tech-events',
        'target_url': 'https://www.meetup.com/find/?source=EVENTS&categoryId=546',
        'sample_file': 'meetup_sample.json',
    },
}

SOURCE_CATEGORIES = {
    'devpost': 'hackathon',
    'devpost_online': 'hackathon',
    'devpost_india': 'hackathon',
    'mlh': 'hackathon',
    'devfolio': 'hackathon',
    'devfolio_open': 'hackathon',
    'devfolio_upcoming': 'hackathon',
    'lablab': 'hackathon',
    'luma': 'tech_event',
    'meetup': 'tech_event',
}
