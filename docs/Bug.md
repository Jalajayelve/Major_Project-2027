# Bug Tracking

## Known issues
### 1. Model artifacts may not match the training data
- Risk: prediction endpoints may fail if model files are missing or mismatched
- Action: verify the model names and expected input columns

### 2. Input validation may need real feature alignment
- Risk: some payloads may fail if they do not match the trained model schema
- Action: align validation logic with actual trained model features

### 3. Sample matching logic is placeholder-only
- Risk: results are heuristic, not based on final university dataset
- Action: replace with real dataset processing when available

### 4. Frontend-only demo flow may not reflect full business rules
- Risk: UI flow can appear complete even if backend logic is still initial
- Action: validate against final requirements and dataset

## Bug status summary
- Open bugs: 4
- Critical: 1
- Medium: 2
- Low: 1

## Resolution priority
1. Validate model file existence and compatibility
2. Align input schema and feature names
3. Replace sample matching set with actual dataset
4. Perform end-to-end validation with real inputs

## Current bug status
The project is functionally structured, but not yet fully validated against final ML data and business rules.
