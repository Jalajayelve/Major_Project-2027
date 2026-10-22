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
→ documents (unavailable until an API exists) → real API analysis → saved dossier.

Matching currently uses the teammate's rule-based catalog endpoint. The expected
MS/MBA prediction model exports and verified Agent 2/7 bundles are missing; the
interface reports these limitations and does not fabricate model results.
