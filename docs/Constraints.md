# Constraints

## Technical constraints
- Backend and frontend are run as separate Python processes
- FastAPI backend must run on port 5000
- Streamlit frontend is expected to call the backend through localhost:5000
- Existing project folders `data/`, `docs/`, and trained model folders must not be overwritten

## Data constraints
- Real model training data must be available before production-grade prediction accuracy can be validated
- Model artifact names and feature formats must match the training script logic
- University matching data is currently a starter dataset and not the final dataset

## Business constraints
- System is intended as a student recommendation and screening tool
- Final output should remain explainable and easy to use by students
- The project should be easy to extend for additional countries, programs, and criteria

## Risk areas
- Missing or inconsistent model feature names
- Incorrect GPA scaling or input validation logic
- Untrained or mismatched `.pkl` model files
- Limited real-world data for final validation

## Project health status
- Functional starter: Yes
- Data-validated model: Not yet
- Production-grade reliability: Not yet
