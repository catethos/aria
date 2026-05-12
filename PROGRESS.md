# ARIA Dashboard — Implementation Progress

**Last updated:** 2026-03-19
**Spec reference:** `spec.txt` (v1.0, March 2026)

---

## What's Built — Mapped to Spec Sections

### Section 2: Data Requirements

| Spec Requirement | Status | Notes |
|---|---|---|
| Role title (required) | Done | Text input in ScoreRoleForm |
| Role ID | Done | Auto-generated integer PK in SQLite |
| Department | Done | Text input in ScoreRoleForm |
| Job grade/level | Partial | Field exists in DB schema and API model but **not exposed in the form UI** |
| Headcount | Partial | Field exists in DB schema and API model (defaults to 1) but **not exposed in the form UI** |
| Role description | Done | Textarea in ScoreRoleForm |
| O\*NET mapping | Not done | Spec Section 2.2 — excluded from demo scope |
| Data preprocessing pipeline (CSV import, dedup, validation) | Not done | Spec Section 2.3 — roles are entered one-by-one via UI |

### Section 3: Scoring Algorithm

| Spec Requirement | Status | Notes |
|---|---|---|
| 6 AIS variables with correct weights | Done | `classifier.py` — CRL 25%, DDS 20%, PRV 20%, SP 15%, PC 10%, RA 10% |
| Inverse transformation for V4, V5, V6 | Done | `adjusted = 100 - raw_score` for social\_perception, physical\_complexity, regulatory\_accountability |
| Composite AIS calculation | Done | Weighted sum matches spec formula exactly |
| 5 APS variables with correct weights | Done | KIP 25%, OQV 25%, DSR 20%, RCW 20%, CCV 10% |
| Composite APS calculation | Done | Direct weighted sum, no inversions |
| LLM-assisted scoring with rubric | Done | BAML `ScoreRole` function with 0-20/21-40/41-60/61-80/81-100 rubric |
| Per-variable justification citing tasks | Done | Each `VariableScore` includes `justification` string |
| Human review of LLM scores | Not done | Spec Section 3.1.2 Step 3 — no score override UI |
| Confidence indicator per variable | Not done | Spec Section 6.2 mentions `"confidence": "high"\|"medium"\|"low"` — not in BAML output |
| Calibration process (5 pilot roles) | Not done | Spec Section 6.3 — no calibration tooling |

### Section 4: ARIA Classification Matrix

| Spec Requirement | Status | Notes |
|---|---|---|
| 3-band thresholds (0-44, 45-64, 65-100) | Done | `classifier.py` `band()` function |
| 9-cell classification lookup | Done | Full matrix in `classifier.py` MATRIX dict |
| 5-tier risk level (Very high to Very low) | Done | `risk_level()` function with correct thresholds |
| Boundary case flagging (within 3 points of threshold) | **Not done** | Spec Section 4.4 — `is_boundary` is in spec pseudocode but not implemented |

### Section 5: Dashboard Views

#### View 1: Executive Summary

| Spec Requirement | Status | Notes |
|---|---|---|
| 4 metric cards | Done | Total Roles, High Risk, High Augment, Priority Action — **enhanced with headcount sub-metrics** |
| ARIA 3x3 matrix with role counts | Done | `AriaMatrix.tsx` — clickable cells filter the table |
| Role table (sortable) | Done | `RoleTable.tsx` — 6 columns, all sortable |
| Department filter (dropdown) | **Not done in UI** | API supports `?dept=` param, but no dropdown in the dashboard |
| Classification filter (dropdown) | **Not done** | Only matrix cell click filtering exists |
| Risk level filter (dropdown) | **Not done** | No UI control |
| Search by role name | **Not done** | No text search input |

#### View 2: Role Detail

| Spec Requirement | Status | Notes |
|---|---|---|
| Role header (title, dept, grade) | Done | `RoleDetail.tsx` slide-in panel — shows title + department. **Grade not displayed.** |
| Classification badge | Done | Colored badge |
| Headcount display | **Not shown** in detail panel | Data exists in API response but not rendered |
| AIS/APS composite score bars | Done | Gradient progress bars with numeric values |
| AIS variable breakdown (6 rows) | Done | `VariableBreakdown.tsx` — raw score, inverse flag, weight, weighted, bar chart, rationale |
| APS variable breakdown (5 rows) | Done | Same component, direct scores |
| Strategic recommendation text | Done | **Enhanced beyond spec** — LLM-generated recommendations with priority, category, affected tasks, productivity gain estimate, transition risk |
| Boundary case amber callout | **Not done** | Spec Section 5.4 View 2 |
| Source indicator (LLM/manual/hybrid) | **Not done** | Spec mentions per-variable source tracking |
| Manual adjustment flag | **Not done** | No score override mechanism |

#### View 3: Distribution Charts

| Spec Requirement | Status | Notes |
|---|---|---|
| AIS histogram | **Not done** | Spec Section 5.4 Chart 1 |
| APS histogram | **Not done** | Spec Section 5.4 Chart 2 |
| AIS vs APS scatter plot | Done | `ScatterPlot.tsx` — dots colored by classification, reference lines at 44/65, tooltip with role name + scores |
| Dot size = headcount | **Not done** | All dots are same size |
| Classification distribution bar chart | **Not done** | Spec Section 5.4 Chart 4 |
| Department comparison grouped bar chart | **Partially done** | `DepartmentHeatmap.tsx` shows per-department avg AIS/APS + headcount bars. Not a grouped bar chart but serves same purpose. |

### Section 5.2: Data Model

| Spec Requirement | Status | Notes |
|---|---|---|
| Departments table | **Not done** | Department is a plain text field on Role, not a separate table |
| Roles table | Done | SQLite via SQLAlchemy ORM — all core fields present |
| AIS variables table | Done | Full per-variable storage with rationale |
| APS variables table | Done | Full per-variable storage with rationale |
| Score adjustments audit trail | **Not done** | Spec Section 5.2 `score_adjustments` table |
| `is_boundary` flag | **Not done** | Column exists in spec but not in implementation |
| `scored_at` timestamp | **Not done** | No timestamp on roles |
| `reviewed_by` / `review_status` | **Not done** | No review workflow |
| `source` field on variables (llm/manual/hybrid) | **Not done** | No source tracking |

### Section 5.3: API Endpoints

| Spec Endpoint | Status | Notes |
|---|---|---|
| `GET /api/roles` with dept/classification/risk filters | Partial | Only `?dept=` supported |
| `GET /api/roles/{id}` | Done | Full variable breakdown |
| `GET /api/summary` | Done | **Enhanced beyond spec** — includes headcount-weighted metrics + per-department stats |
| `GET /api/matrix` | Done | Merged into `/api/summary` as `matrix_counts` |
| `GET /api/departments` | Done | Merged into `/api/summary` as `departments` array |
| `POST /api/score-role` (SSE streaming) | Done | **Beyond spec** — spec assumed pre-scored data; this does real-time LLM scoring |

---

## Enhancements Beyond Spec

These features were added but are **not in the original spec**:

1. **Real-time LLM scoring via SSE** — The spec assumed a batch-scored dataset. The app scores roles live with streaming progress UI showing tasks, variables, and recommendations appearing incrementally.
2. **Task-level categorization** — Each extracted task is tagged as Automatable / Augmentable / Human Essential with a visual breakdown bar and per-task color indicators.
3. **LLM-generated recommendations** — A second LLM call (`GenerateRecommendations`) produces 3-6 actionable recommendations per role with priority, category, affected tasks, productivity gain estimate, and transition risk. These stream in incrementally card-by-card with live content updates.
4. **Headcount-weighted exposure metrics** — Metric cards show both role counts AND headcount-weighted figures. Summary API returns per-department headcount exposure.
5. **Department heatmap** — Visual component showing department-level risk exposure with headcount bars and risk distribution mini-bars.

---

## What's Missing

### High Priority (in spec, not built)

- Boundary case flagging (Section 4.4) — roles within 3 points of band thresholds should be flagged
- Filter dropdowns for department / classification / risk level (Section 5.4)
- Text search for role name (Section 5.4)
- Grade and headcount fields exposed in the scoring form UI
- Grade and headcount displayed in role detail panel
- Score override / human review workflow (Section 3.1.2, 6.1)

### Medium Priority (in spec, not built)

- AIS/APS histogram charts (Section 5.4 Charts 1-2)
- Classification distribution bar chart (Section 5.4 Chart 4)
- Scatter plot dot size proportional to headcount (Section 5.4 Chart 3)
- Audit trail for score adjustments (Section 5.2 `score_adjustments` table)
- Source indicator per variable — LLM / manual / hybrid (Section 5.4 View 2)
- `scored_at` timestamp on roles
- `reviewed_by` / `review_status` fields

### Low Priority / Phase 2 (acknowledged as out of scope in spec)

- O\*NET task taxonomy mapping (Section 2.2)
- CSV/Excel import and batch scoring (Section 2.3)
- Authentication and permissions (Section 7.1)
- Calibration tooling for pilot roles (Section 6.3)
- Skills adjacency / gap analysis (Section 1.2)
- Role transition simulator (Section 1.2)
- Scenario modelling (Section 1.2)

---

## Architecture Overview

```
CPFB/
├── baml_src/                          # BAML type definitions & LLM functions
│   ├── clients.baml                   # Claude client (OpenRouter, Sonnet 4.6)
│   ├── score_role.baml                # ScoreRole + GenerateRecommendations functions
│   └── main.baml                      # Generator config (Python/Pydantic output)
│
├── backend/                           # FastAPI + SQLite
│   ├── main.py                        # 5 API endpoints + SSE streaming
│   ├── database.py                    # SQLAlchemy models (Role, AISVariable, APSVariable)
│   ├── classifier.py                  # Pure Python ARIA classification logic
│   └── aria.db                        # SQLite database (auto-created)
│
└── frontend/                          # React 19 + TypeScript + Vite + Tailwind
    └── src/
        ├── App.tsx                    # Root component
        ├── main.tsx                   # React entry point
        ├── api.ts                     # API client + SSE consumer
        ├── types.ts                   # TypeScript interfaces + color constants
        ├── index.css                  # Tailwind + custom animations
        ├── pages/
        │   └── Dashboard.tsx          # Main page coordinator
        └── components/
            ├── MetricCards.tsx         # 4 summary KPI cards (with headcount)
            ├── AriaMatrix.tsx         # 3x3 classification grid (clickable)
            ├── RoleTable.tsx          # Sortable role table (6 columns)
            ├── RoleDetail.tsx         # Slide-in panel (scores, tasks, recs)
            ├── ScatterPlot.tsx        # AIS vs APS scatter (Recharts)
            ├── ScoreRoleForm.tsx       # Modal form for new role input
            ├── ScoringProgress.tsx     # Real-time scoring progress modal
            ├── VariableBreakdown.tsx   # AIS/APS variable detail bars
            └── DepartmentHeatmap.tsx   # Department exposure visualization
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite 6.3, Tailwind CSS 4.2, Recharts 3.8 |
| Backend | FastAPI, SQLAlchemy, SQLite, SSE-Starlette, Uvicorn |
| LLM | BAML 0.220 with Claude Sonnet 4.6 via OpenRouter |
| Package manager | uv (Python), npm (Node) |
