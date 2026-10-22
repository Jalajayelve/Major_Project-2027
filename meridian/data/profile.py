"""Original form schema with optional persisted preferences; no demo identities."""
from copy import deepcopy
import pycountry
from .mock import FORM_SCHEMA as ORIGINAL, _F

FORM_SCHEMA = deepcopy(ORIGINAL)
FORM_SCHEMA[0]['fields'].extend([
    _F('phone_code', 'Calling code', 'select', options=['+1', '+44', '+91', '+61', '+49', '+33', '+86', '+81', '+65', '+971']),
    _F('country', 'Country of residence'),
])
FORM_SCHEMA[1]['fields'].extend([_F('board', 'Education board'), _F('degree_level', 'Current degree level', 'select', options=['Bachelors', 'Masters', 'Doctorate', 'Other'])])
FORM_SCHEMA[3]['fields'].extend([_F('internship_details', 'Internship details', 'textarea', wide=True), _F('research_experience', 'Research experience (numeric API input; optional)')])
FORM_SCHEMA[4]['fields'].extend([_F('essay_score', 'Essay score (only if supplied by an evaluator; MBA API input)'), _F('match_country', 'Matching country', 'select', options=['USA', 'Canada', 'UK', 'Australia', 'all']), _F('match_tier', 'Catalog tier filter', 'select', options=['low', 'medium', 'high', 'elite'])])
FORM_SCHEMA[6]['fields'].extend([_F('accommodation', 'Accommodation preference', 'select', options=['On campus', 'Shared apartment', 'Private apartment', 'No preference']), _F('commute', 'Commute preference', 'select', options=['Walking', 'Cycling', 'Public transport', 'Car', 'No preference']), _F('commute_minutes', 'Maximum commute (minutes)', 'number')])
for section in FORM_SCHEMA:
    for field in section['fields']:
        if field['key'] == 'funding':
            field.update(kind='select', options=['Self-funded', 'Education loan', 'Savings + education loan', 'Scholarship', 'Undecided'])

COUNTRIES = sorted(country.name for country in pycountry.countries)
REGIONS = ['United States', 'Canada', 'United Kingdom', 'Europe', 'Australia', 'New Zealand', 'Asia', 'California', 'Texas', 'Northeast']


def empty_profile():
    return {f['key']: '' for s in FORM_SCHEMA for f in s['fields']}
