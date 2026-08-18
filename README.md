# Study Abroad AI

This project is a Python capstone project for predicting suitable study-abroad programs and matching students to universities based on profile data.

## Project structure

```text
study-abroad-ai/
├── backend/                          # FastAPI REST API
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── profile_routes.py
│   │   │   ├── matching_routes.py
│   │   │   └── health_routes.py
│   │   ├── agents/
│   │   │   ├── profile_agent/
│   │   │   │   ├── predict.py
│   │   │   │   ├── train.py
│   │   │   │   └── trained_models/
│   │   │   └── matching_agent/
│   │   │       └── match.py
│   │   ├── db/
│   │   │   ├── models.py
│   │   │   └── session.py
│   │   └── utils/
│   │       └── preprocessing.py
│   ├── tests/
│   │   └── test_app.py
│   └── requirements.txt
├── frontend/
│   ├── streamlit_app.py
│   ├── pages/
│   │   ├── 1_Profile_Form.py
│   │   ├── 2_Recommendations.py
│   │   └── 3_About.py
│   ├── utils/
│   │   └── api_client.py
│   └── requirements.txt
├── data/
│   ├── raw/
│   └── processed/
├── docs/
├── .gitignore
├── README.md
└── backend/app/agents/profile_agent/trained_models/
```

## Local development setup

### 1) Backend

From the project root:

```bash
cd study-abroad-ai/backend
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# or .venv\Scripts\activate  # Windows
pip install -r requirements.txt
python app/main.py
```

This starts the FastAPI API on:

```text
http://localhost:5000
```

### 2) Frontend

Open a second terminal, then run:

```bash
cd study-abroad-ai/frontend
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# or .venv\Scripts\activate  # Windows
pip install -r requirements.txt
streamlit run streamlit_app.py
```

This starts the Streamlit UI on:

```text
http://localhost:8501
```

The frontend is configured to call the backend at:

```text
http://localhost:5000
```

## API overview

The backend exposes the following routes:

- `GET /health` — health check
- `POST /predict/ms` — predict MS admission suitability
- `POST /predict/mba` — predict MBA admission suitability
- `POST /match` — fetch university matches by tier

## Notes

- The `data/`, `docs/`, and trained model directories are intentionally left alone and are assumed to already contain project content.
- The app is scaffolded with starter implementations so you can extend the logic for your capstone.
