# Typst PDF Report Template

This folder contains the first PDF-oriented renderer for the ARIA report content packet.

## Generate sample content

From the repository root:

```bash
backend/.venv/bin/python backend/export_report_content.py \
  --type org \
  --organisation-name CPFB \
  --output reports/generated/org_report_sample.json

backend/.venv/bin/python backend/export_report_content.py \
  --type role \
  --role-id 1 \
  --output reports/generated/role_report_sample.json
```

## Render PDF

```bash
typst compile --root reports reports/typst/org-report.typ reports/generated/org_report_sample.pdf
typst compile --root reports reports/typst/role-report.typ reports/generated/role_report_sample.pdf
```

The Typst templates read JSON snapshots under `reports/generated/`, created from the backend report-content builder. The database remains the working source of truth.

## Persisted report runs

The backend can now create database report runs and render PDFs from those run payloads:

```bash
backend/.venv/bin/python - <<'PY'
import os, sys
sys.path.insert(0, "backend")
os.chdir("backend")

from database import init_db, SessionLocal, Role
from report_runs import create_org_report_run, render_report_pdf

init_db()
db = SessionLocal()
try:
    roles = db.query(Role).order_by(Role.id.asc()).all()
    run = create_org_report_run(
        db,
        roles,
        {"organisation_name": "CPFB", "organisation_descriptor": "AI impact assessment portfolio"},
        {},
    )
    artifact = render_report_pdf(db, "organisation", run.id)
    print(run.id)
    print(artifact.file_path)
finally:
    db.close()
PY
```

API surfaces:

- `POST /api/reports/roles/{role_id}/runs?render_pdf=true`
- `GET /api/report-runs/roles/{run_id}`
- `POST /api/report-runs/roles/{run_id}/review`
- `POST /api/report-runs/roles/{run_id}/freeze`
- `POST /api/report-runs/roles/{run_id}/render`
- `POST /api/reports/org/runs`
- `GET /api/report-runs/org/{run_id}`
- `POST /api/report-runs/org/{run_id}/review`
- `POST /api/report-runs/org/{run_id}/freeze`
- `POST /api/report-runs/org/{run_id}/render`
- `GET /api/report-artifacts/{artifact_id}`

Run snapshots are written to `reports/generated/runs/`; rendered PDFs are written to `reports/generated/renders/<run-id>/` and recorded in the `rendered_artifacts` table with a content hash.
Organisation report runs prefer frozen or reviewed role insight runs for the current methodology version. Pass `require_reviewed_role_runs: true` to `POST /api/reports/org/runs` when the report should fail instead of falling back to generated role runs.
