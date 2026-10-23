# Test Checklist

## Backend checklist
- [ ] Health endpoint returns 200
- [ ] /predict/ms accepts valid student profile payload
- [ ] /predict/mba accepts valid student profile payload
- [ ] /match returns a filtered university list
- [ ] Invalid payload returns clean validation error
- [ ] Model path is available when prediction is executed

## Frontend checklist
- [ ] Streamlit app loads successfully
- [ ] Profile form renders correctly
- [ ] MS/MBA branching fields function as expected
- [ ] Recommendation page loads matched universities
- [ ] API client connects to localhost:5000 correctly

## Integration checklist
- [ ] Backend server runs on port 5000
- [ ] Frontend calls backend successfully
- [ ] Sample prediction request succeeds end-to-end
- [ ] Sample recommendation request succeeds end-to-end

## Completion checklist
- [ ] Real model files validated
- [ ] Project dataset finalized
- [ ] Matching dataset finalized
- [ ] Final ML metrics reviewed
- [ ] Final capstone report prepared

## Current stage
In progress: starter demo flow works and project tracking documents are in place.
Pending: final real-data and model validation.
