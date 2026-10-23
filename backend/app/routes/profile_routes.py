from fastapi import APIRouter, HTTPException
import logging

from app.agents.profile_agent.predict import predict_profile_outcome

router = APIRouter()


@router.post("/predict/ms")
def predict_ms(payload: dict):
    try:
        return predict_profile_outcome(payload, program_type="ms")
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="MS prediction unavailable: genuine ms_model.pkl export is missing. "
            "The bundled candidate-tier artifacts are not compatible with MS outcome prediction.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        logging.getLogger(__name__).exception('MS prediction failed')
        raise HTTPException(status_code=503, detail="Prediction model could not be loaded or run. Check the backend logs and model environment.") from exc


@router.post("/predict/mba")
def predict_mba(payload: dict):
    try:
        return predict_profile_outcome(payload, program_type="mba")
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="MBA prediction unavailable: genuine mba_model.pkl export is missing. "
            "The bundled candidate-tier artifacts are not compatible with MBA outcome prediction.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        logging.getLogger(__name__).exception('MBA prediction failed')
        raise HTTPException(status_code=503, detail="Prediction model could not be loaded or run. Check the backend logs and model environment.") from exc
