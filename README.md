# MERIDIAN (Python Reflex)

    pip install -r requirements.txt
    reflex run

Flow: / Landing -> /profile -> /documents -> /analysis (7 agents) -> /results -> /report (PDF download)

- meridian/theme.py: every colour token + global CSS (set ACCENT to your exact symbol hex)
- meridian/data/mock.py: all mock data
- meridian/services/: interfaces.py (REST / WebSocket / report Protocols + event shape), mock.py (dev stand-ins).
  Return real clients from services/__init__.py to connect FastAPI / LangGraph.
- assets/scene.js: hero parallax + lazy Three.js globe (skipped on mobile / reduced motion)
