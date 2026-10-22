# Architecture

## Overview
The Study Abroad AI project is a two-part application:
- Backend: FastAPI service that exposes prediction and matching endpoints
- Frontend: Streamlit UI that collects student inputs and displays recommendations
- Data/ML layer: local model artifacts and preprocessing utilities

## High-level architecture

```text
Streamlit UI
   |
   v
HTTP requests to FastAPI backend
   |
   v
Routes -> ML agents -> preprocessing/utilities
   |
   v
Data and model artifacts
```

## Components
### 1. Backend
- `backend/app/main.py`: app startup entry
- `backend/app/routes/*.py`: request handlers for health, prediction, and matching
- `backend/app/agents/profile_agent/predict.py`: model loading and inference
- `backend/app/agents/matching_agent/match.py`: university-tier matching logic
- `backend/app/utils/preprocessing.py`: input normalization and validation

### 2. Frontend
- `frontend/streamlit_app.py`: landing/home page
- `frontend/pages/1_Profile_Form.py`: MS/MBA branching form
- `frontend/pages/2_Recommendations.py`: recommendations display
- `frontend/utils/api_client.py`: backend API wrapper

### 3. Data and models
- `data/raw/`: raw dataset files
- `data/processed/`: processed inputs
- `backend/app/agents/profile_agent/trained_models/`: saved model artifacts

## Current implementation status
- Project scaffold: Complete
- API structure: Complete
- UI structure: Complete
- Model inference integration: Starter implementation ready
- Dataset/model training: Pending real project data integration

## Completion estimate
- Overall project completion: 60-70%
- Enough for starter/demo flow and capstone structure
- Real ML model accuracy and final university matching requires real data and trained artifacts
