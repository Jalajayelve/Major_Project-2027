# Decisions

## Decision 1: Use FastAPI for backend
- Reason: lightweight API setup, quick integration with Python ML workflows
- Impact: backend is easier to extend and maintain than a minimal Flask prototype

## Decision 2: Use Streamlit for frontend
- Reason: low setup effort for interactive capstone demos
- Impact: frontend is easy to build and test without a complex React application

## Decision 3: Keep the existing data and model directories unchanged
- Reason: those folders already contain real project assets and should not be overwritten
- Impact: project structure stays safe while allowing new code to be layered around it

## Decision 4: Start with starter logic and demo flow
- Reason: the project can be structured and tested before final real-data integration
- Impact: early implementation is functional but still needs production-grade ML data

## Decision 5: Track completion with documentation files
- Reason: the team needs to see what is complete, what is pending, and where the current bottlenecks are
- Impact: easier project status tracking and future handoff review

## Current status
The architecture decisions support a demo-ready capstone project, but the final accuracy and full recommendation engine still depend on real model training and data validation.
