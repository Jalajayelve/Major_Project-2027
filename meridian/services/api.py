"""HTTP boundary with finite deadlines and explicit profile input mapping."""
import os
import math
import httpx


def number(profile, key, low, high):
    try:
        value = float(profile.get(key, ''))
    except (ValueError, TypeError):
        raise ValueError(f'Enter {key.replace("_", " ")} in your profile.') from None
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{key} must be between {low:g} and {high:g}.')
    return value


def gpa(profile):
    scale = number(profile, 'gpa_scale', 4, 100)
    if scale not in (4, 10, 100):
        raise ValueError('Choose GPA scale 4, 10, or 100.')
    return number(profile, 'gpa', 0, scale) / scale * 4


def prediction_payload(profile):
    payload = {'gpa': gpa(profile), 'work_experience': number(profile, 'work_years', 0, 80)}
    if profile.get('degree_goal') == 'MBA':
        payload.update(gmat_score=number(profile, 'gmat', 200, 800), essay_score=number(profile, 'essay_score', 0, 100))
    elif profile.get('degree_goal') == 'MS':
        payload.update(gre_score=number(profile, 'gre_verbal', 130, 170)+number(profile, 'gre_quant', 130, 170),
                       toefl_score=number(profile, 'toefl', 0, 120), research_experience=number(profile, 'research_experience', 0, 80))
    else:
        raise ValueError('Select MS or MBA in Study goals.')
    return payload


async def request(path, payload):
    base = os.environ.get('MERIDIAN_API_URL', 'http://127.0.0.1:8001').rstrip('/')
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(45, connect=5), trust_env=False) as client:
            response = await client.post(base+path, json=payload)
        if response.status_code >= 400:
            try:
                detail = response.json().get('detail', 'Request failed')
            except ValueError:
                detail = 'Request failed'
            raise ValueError(f'Analysis API ({response.status_code}): {detail}')
        result = response.json()
        if not isinstance(result, dict):
            raise ValueError('The API returned an invalid response.')
        return result
    except httpx.TimeoutException:
        raise ValueError('Analysis timed out. Retry when the backend is ready.') from None
    except httpx.HTTPError:
        raise ValueError('Cannot reach the analysis API. Check MERIDIAN_API_URL and start the backend, then retry.') from None
