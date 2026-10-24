from fastapi import APIRouter, HTTPException
import logging

from app.agents.profile_agent.predict import predict_candidate_tier, predict_profile_outcome
from app.agents.program_agent.program import rank_programs
from app.agents.career_agent.career import analyze_career
from app.agents.financial_agent.financial import analyze_financial, FinancialUnavailable
from app.agents.scholarship_agent.scholarship import analyze_scholarships, ScholarshipUnavailable

router = APIRouter()


@router.post("/agent3/program")
def agent3_program(payload: dict):
    try:
        return rank_programs(payload.get("profile", {}), payload.get("matched_universities", []))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="Agent 3 catalog or artifacts are unavailable.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        logging.getLogger(__name__).exception("Agent 3 failed")
        raise HTTPException(status_code=503, detail="Agent 3 could not complete program ranking.") from exc


@router.post("/agent1/profile")
def agent1_profile(payload: dict):
    try:
        return predict_candidate_tier(payload)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="Agent 1 candidate-tier artifacts are unavailable.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        logging.getLogger(__name__).exception("Agent 1 failed")
        raise HTTPException(status_code=503, detail="Agent 1 could not complete analysis.") from exc


@router.post("/agent6/career")
def agent6_career(payload: dict):
    try:
        return analyze_career(payload.get("profile", {}))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="Agent 6 career artifacts are unavailable.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        logging.getLogger(__name__).exception("Agent 6 failed")
        raise HTTPException(status_code=503, detail="Agent 6 could not complete career analysis.") from exc


@router.post("/agent4/financial")
def agent4_financial(payload: dict):
    try:
        return analyze_financial(payload)
    except FinancialUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="Agent 4 model artifacts are unavailable.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        logging.getLogger(__name__).exception("Agent 4 failed")
        raise HTTPException(status_code=503, detail="Agent 4 could not complete financial analysis.") from exc


@router.post("/agent5/scholarship")
def agent5_scholarship(payload: dict):
    try:
        return analyze_scholarships(payload)
    except ScholarshipUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        logging.getLogger(__name__).exception("Agent 5 failed")
        raise HTTPException(status_code=503, detail="Agent 5 could not complete scholarship analysis.") from exc


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
