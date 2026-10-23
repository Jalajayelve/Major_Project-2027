"""Optional profile fields are validated when supplied, including on save."""
import math
import re
from ..data.profile import FORM_SCHEMA
from .storage import valid_email

FIELDS = {f['key']: f for section in FORM_SCHEMA for f in section['fields']}
RANGES = {'gre_verbal': (130, 170), 'gre_quant': (130, 170), 'gre_awa': (0, 6),
          'toefl': (0, 120), 'ielts': (0, 9), 'gmat': (200, 800),
          'leadership_score': (0, 10), 'research_score': (0, 10),
          'competition_score': (0, 10), 'volunteering_score': (0, 10),
          'publication_count': (0, 2**31-1), 'patent_count': (0, 2**31-1)}
NONNEGATIVE = ('budget', 'work_years', 'internships', 'backlogs', 'commute_minutes', 'research_experience')


def profile_errors(profile):
    errors = {}
    for key, value in profile.items():
        if key not in FIELDS or not isinstance(value, str):
            errors[key] = 'Unknown profile field or invalid value.'
            continue
        if not value.strip():
            continue
        if len(value) > 10000:
            errors[key] = 'Please shorten this field to 10,000 characters.'
        if FIELDS[key]['kind'] == 'select' and value not in FIELDS[key]['options']:
            errors[key] = 'Choose one of the listed options.'
    if profile.get('email') and not valid_email(profile['email']):
        errors['email'] = 'Enter a valid email address.'
    if profile.get('phone'):
        phone = profile['phone'].strip()
        digits = re.sub(r'\D', '', phone)
        if not re.fullmatch(r'\+?[\d ()\-]+', phone) or not 6 <= len(digits) <= 15:
            errors['phone'] = 'Enter a phone number with 6–15 digits; spaces, parentheses and hyphens are allowed.'
    ranges = {**RANGES, **{k: (0, math.inf) for k in NONNEGATIVE}}
    if profile.get('degree_goal') == 'MBA':
        ranges['essay_score'] = (-math.inf, math.inf)  # no rubric supplied by backend
    if profile.get('gpa'):
        if profile.get('gpa_scale') not in ('4', '10', '100'):
            errors['gpa_scale'] = 'Choose the scale used for this academic score.'
        else:
            ranges['gpa'] = (0, float(profile['gpa_scale']))
    for key, (low, high) in ranges.items():
        if not profile.get(key, '').strip():
            continue
        try:
            number = float(profile[key])
            if not math.isfinite(number) or not low <= number <= high:
                raise ValueError()
            if key in ('internships', 'backlogs', 'commute_minutes', 'publication_count', 'patent_count') and not number.is_integer():
                errors[key] = 'Enter a whole number.'
        except (ValueError, TypeError):
            errors[key] = f'Enter a number from {low:g} to {high:g}.' if math.isfinite(high) else 'Enter a finite, nonnegative number.'
    return errors
