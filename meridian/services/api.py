"""HTTP boundary with finite deadlines and explicit profile input mapping."""
import os
import math
import logging
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
    payload = {'gpa': gpa(profile), 'work_experience': number(profile, 'work_years', 0, math.inf)}
    if profile.get('degree_goal') == 'MBA':
        payload.update(gmat_score=number(profile, 'gmat', 200, 800), essay_score=number(profile, 'essay_score', -math.inf, math.inf))
    elif profile.get('degree_goal') == 'MS':
        payload.update(gre_score=number(profile, 'gre_verbal', 130, 170)+number(profile, 'gre_quant', 130, 170),
                       toefl_score=number(profile, 'toefl', 0, 120), research_experience=number(profile, 'research_experience', 0, math.inf))
    else:
        raise ValueError('Select MS or MBA in Study goals.')
    return payload


def agent1_payload(profile):
    degree = str(profile.get("degree_goal", "")).upper()
    if degree not in {"MS", "MBA"}:
        raise ValueError("Select MS or MBA in Study goals.")
    payload = {
        "track": degree,
        "gpa_normalized_4": gpa(profile),
        "toefl_score": number(profile, "toefl", 0, 120) if profile.get("toefl") else 0,
        "has_research": 1 if profile.get("research_experience", "").strip() not in ("", "0") else 0,
        "work_experience_months": number(profile, "work_years", 0, math.inf) * 12 if profile.get("work_years") else 0,
        "major": "Business" if "business" in profile.get("field", "").lower() else
                 "STEM" if profile.get("field") else "NA",
    }
    if degree == "MS":
        payload["gre_score"] = (
            number(profile, "gre_verbal", 130, 170)
            + number(profile, "gre_quant", 130, 170)
            if profile.get("gre_verbal") and profile.get("gre_quant") else 0
        )
    else:
        payload["gmat_score"] = number(profile, "gmat", 200, 800) if profile.get("gmat") else 0
    return payload


async def request(path, payload):
    base = os.environ.get('MERIDIAN_API_URL', 'http://127.0.0.1:8001').rstrip('/')
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(45, connect=5), trust_env=False) as client:
            response = await client.post(base+path, json=payload)
        if response.status_code >= 400:
            try:
                body = response.json()
                detail = body.get('detail', 'Request failed') if isinstance(body, dict) else 'Request failed'
            except ValueError:
                detail = 'Request failed'
            if response.status_code == 401:
                detail = 'The analysis service rejected authorization. Check the service configuration.'
            raise ValueError(f'Analysis API ({response.status_code}): {detail}')
        try:
            result = response.json()
        except ValueError:
            raise ValueError('The analysis API returned an unreadable response. Please retry.') from None
        if not isinstance(result, dict):
            raise ValueError('The API returned an invalid response.')
        if path == '/match':
            rows = result.get('matched_universities')
            if not isinstance(rows, list) or any(not isinstance(row, dict) or any(not isinstance(row.get(k), str) or not row[k] for k in ('name', 'country', 'tier')) or not isinstance(row.get('gpa'), (int, float)) or not math.isfinite(row['gpa']) for row in rows):
                raise ValueError('The matching API returned an invalid university list.')
        elif path in ('/predict/ms', '/predict/mba', '/agent1/profile'):
            if not isinstance(result.get('prediction'), str) or not result['prediction']:
                raise ValueError('The profile analysis API returned an empty or invalid result.')
            probability = result.get('probability')
            if probability is not None and (type(probability) not in (int, float) or not math.isfinite(probability) or not 0 <= probability <= 1):
                raise ValueError('The prediction API returned invalid confidence data.')
        elif path == '/agent3/program':
            if not isinstance(result.get('programs'), list):
                raise ValueError('The program API returned an invalid program list.')
        return result
    except httpx.TimeoutException:
        raise ValueError('Analysis timed out. Retry when the backend is ready.') from None
    except httpx.HTTPError:
        raise ValueError('Cannot reach the analysis API. Check MERIDIAN_API_URL and start the backend, then retry.') from None
