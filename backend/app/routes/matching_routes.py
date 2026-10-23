from fastapi import APIRouter, HTTPException
import math
import logging

from app.agents.university_matching_agent.match import match_universities

router = APIRouter()


@router.post("/match")
async def match(payload: dict):
    try:
        if 'gpa' not in payload or isinstance(payload['gpa'], bool):
            raise ValueError('GPA on a 4-point scale is required.')
        try:
            gpa = float(payload['gpa'])
        except (TypeError, ValueError):
            raise ValueError('GPA must be numeric.') from None
        if not math.isfinite(gpa) or not 0 <= gpa <= 4:
            raise ValueError('GPA must be between 0 and 4.')
        if not isinstance(payload.get('country', 'USA'), str) or not payload.get('country', 'USA').strip():
            raise ValueError('Country must be a nonempty string.')
        if payload.get('tier', 'medium') not in ('low', 'medium', 'high', 'elite'):
            raise ValueError('Tier must be low, medium, high or elite.')
        return match_universities(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        logging.getLogger(__name__).exception('Matching failed')
        raise HTTPException(status_code=500, detail="Matching could not complete. Please retry.") from exc
