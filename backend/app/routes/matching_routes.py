from fastapi import APIRouter, HTTPException

from app.agents.matching_agent.match import match_universities

router = APIRouter()


@router.post("/match")
async def match(payload: dict):
    try:
        return match_universities(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Matching failed: {str(exc)}") from exc
