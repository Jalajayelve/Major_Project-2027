# MERIDIAN — integrated Python Reflex application

The original `meridian-redesign` frontend is the foundation. Backend services and
model artifacts were selectively imported from `jalaja-backend`.

Read the [integration report and Windows run guide](docs/Meridian-Integration.md)
for setup, implemented features, verified tests, backend limitations and file details.

Run the backend and frontend in separate VS Code PowerShell terminals:

```powershell
.\scripts\start_meridian.ps1 -Service backend
.\scripts\start_meridian.ps1 -Service frontend
```

Install each environment first using the guide. Open http://localhost:3000.

Flow: landing → cinematic transition → login/registration → dashboard → profile
→ private document upload and text preview → real API analysis → saved dossier.

Matching uses the existing rule-based catalog endpoint, followed by Agent 3
program ranking. Agent 7 now scores documented extracurricular inputs with its
verified recovered bundle and saves results to the dossier and PDF. See the
[Agent 7 setup and verification report](docs/Agent7-Application-Integration.md).
The separate MS/MBA outcome exports and optional experimental Agent 2 bundle
remain unavailable; no substitute predictions are generated.
