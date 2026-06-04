"""Export report content packets for rendering.

This is a small utility for local renderer workflows. The database remains the
working source of truth; exported JSON is a reproducible snapshot that Typst or
another renderer can consume.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export ARIA report content JSON.")
    parser.add_argument("--type", choices=["org", "role"], required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--organisation-name", default="CPFB")
    parser.add_argument("--role-id", type=int)
    args = parser.parse_args()

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    os.chdir(Path(__file__).parent)

    from database import Role, RoleInsightRun, SessionLocal
    from report_content import (
        METHODOLOGY_VERSION,
        build_org_report_content,
        build_org_report_content_from_role_insight_runs,
        build_role_report_content,
    )

    session = SessionLocal()
    try:
        if args.type == "role":
            if args.role_id is None:
                raise SystemExit("--role-id is required for role exports")
            role = session.query(Role).filter(Role.id == args.role_id).first()
            if role is None:
                raise SystemExit(f"Role {args.role_id} not found")
            packet = build_role_report_content(role)
        else:
            roles = session.query(Role).order_by(Role.id.asc()).all()
            stable_runs = []
            for role in roles:
                run = (
                    session.query(RoleInsightRun)
                    .filter(RoleInsightRun.role_id == role.id)
                    .filter(RoleInsightRun.methodology_version == METHODOLOGY_VERSION)
                    .filter(RoleInsightRun.status.in_(("frozen", "reviewed")))
                    .order_by(RoleInsightRun.generated_at.desc())
                    .first()
                )
                if run is None:
                    stable_runs = []
                    break
                stable_runs.append(run)
            organisation_context = {
                "organisation_name": args.organisation_name,
                "organisation_descriptor": "AI impact assessment portfolio",
            }
            if stable_runs:
                packet = build_org_report_content_from_role_insight_runs(
                    stable_runs,
                    organisation_context=organisation_context,
                    report_config={},
                )
            else:
                packet = build_org_report_content(
                    roles,
                    organisation_context=organisation_context,
                    report_config={},
                )
    finally:
        session.close()

    output_path.write_text(json.dumps(packet, indent=2), encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
