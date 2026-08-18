from fastapi import APIRouter, HTTPException

from app.agents.profile_agent.predict import predict_profile_outcome

router = APIRouter()


@router.post("/predict/ms")
async def predict_ms(payload: dict):
    try:
        return predict_profile_outcome(payload, program_type="ms")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(exc)}") from exc


@router.post("/predict/mba")
async def predict_mba(payload: dict):
    try:
        return predict_profile_outcome(payload, program_type="mba")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(exc)}") from exc
