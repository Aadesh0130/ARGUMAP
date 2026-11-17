"""ARGUMAP Human Annotation Workspace Server & CLI Launcher.

Provides a lightweight, dedicated, local web interface and CLI tool to enable two human
annotators (Annotator A and Annotator B) to independently label argument components and relations
on the verified UK Hansard AI debate pilot package.

Usage (PowerShell):
  # Annotator A session
  python scripts/annotation/annotation_workspace.py --annotator A

  # Annotator B session
  python scripts/annotation/annotation_workspace.py --annotator B

  # Specify custom port
  python scripts/annotation/annotation_workspace.py --annotator A --port 8765

  # CLI inspection flags
  python scripts/annotation/annotation_workspace.py --annotator A --status
  python scripts/annotation/annotation_workspace.py --annotator A --validate
  python scripts/annotation/annotation_workspace.py --annotator A --export
"""

import argparse
from pathlib import Path
import sys
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.annotation.workspace_session import WorkspaceSession, VALID_ANNOTATORS

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
WORKSPACE_HTML_PATH = TEMPLATES_DIR / "workspace.html"


class UnitUpdatePayload(BaseModel):
    label: Optional[str] = Field(None, description="Frozen component label or null")
    confidence: Optional[float] = Field(1.0, ge=0.0, le=1.0)
    note: Optional[str] = Field(None, description="Annotator ambiguity note or rationale")


class RelationUpdatePayload(BaseModel):
    label: Optional[str] = Field(None, description="Frozen relation label or null")
    confidence: Optional[float] = Field(1.0, ge=0.0, le=1.0)
    note: Optional[str] = Field(None, description="Override justification or rationale")
    is_override: Optional[bool] = Field(None)


def create_annotation_app(
    annotator_id: str,
    workspace_dir: Optional[Path] = None,
    template_dir: Optional[Path] = None,
    submissions_dir: Optional[Path] = None,
) -> FastAPI:
    """Builds and configures the FastAPI application for an isolated annotator session."""
    session = WorkspaceSession(
        annotator_id=annotator_id,
        workspace_dir=workspace_dir,
        template_dir=template_dir,
        submissions_dir=submissions_dir,
    )

    app = FastAPI(
        title=f"ARGUMAP Annotation Workspace — {annotator_id}",
        description="Local independent human annotation interface for ARGUMAP Hansard pilot.",
        version="1.0.0",
    )

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        if not WORKSPACE_HTML_PATH.exists():
            raise HTTPException(status_code=500, detail="workspace.html template missing")
        with open(WORKSPACE_HTML_PATH, "r", encoding="utf-8") as f:
            return f.read()

    @app.get("/api/session")
    def get_session_info() -> Dict[str, Any]:
        return session.get_summary()

    @app.get("/api/units")
    def list_units() -> list:
        return session.get_units()

    @app.get("/api/units/{unit_id}")
    def get_unit_detail(unit_id: str) -> Dict[str, Any]:
        u = session.get_unit(unit_id)
        if not u:
            raise HTTPException(status_code=404, detail=f"Unit '{unit_id}' not found")
        return u

    @app.post("/api/units/{unit_id}")
    def update_unit_label(unit_id: str, payload: UnitUpdatePayload) -> Dict[str, Any]:
        try:
            return session.update_unit(
                unit_id=unit_id,
                label=payload.label,
                confidence=payload.confidence,
                note=payload.note,
            )
        except (KeyError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/api/relations")
    def list_relations(
        filter_mode: str = Query("all", description="Filter: all, unannotated, labeled, overrides, cross_turn, intra_turn"),
        offset: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=1300),
    ) -> Dict[str, Any]:
        return session.get_relations(filter_mode=filter_mode, offset=offset, limit=limit)

    @app.get("/api/relations/{source_id}/{target_id}")
    def get_relation_detail(source_id: str, target_id: str) -> Dict[str, Any]:
        r = session.get_relation(source_id, target_id)
        if not r:
            raise HTTPException(status_code=404, detail=f"Candidate pair ({source_id} -> {target_id}) not found")
        return r

    @app.post("/api/relations/{source_id}/{target_id}")
    def update_relation_label(
        source_id: str, target_id: str, payload: RelationUpdatePayload
    ) -> Dict[str, Any]:
        try:
            return session.update_relation(
                source_id=source_id,
                target_id=target_id,
                label=payload.label,
                confidence=payload.confidence,
                note=payload.note,
                is_override=payload.is_override,
            )
        except (KeyError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/save")
    def save_draft() -> Dict[str, Any]:
        path = session.save_working_copy()
        return {"status": "saved", "path": str(path), "summary": session.get_summary()}

    @app.get("/api/validate")
    def run_validation() -> Dict[str, Any]:
        return session.validate_session()

    @app.post("/api/export")
    def export_submission() -> Dict[str, Any]:
        success, msg, path = session.export_completed_package()
        if not success:
            raise HTTPException(status_code=400, detail=msg)
        return {"status": "exported", "message": msg, "path": str(path)}

    return app


def parse_annotator_arg(val: str) -> str:
    """Normalizes 'A', 'B', 'annotator_A', 'annotator_B' into official ID."""
    norm = val.strip().lower()
    if norm in ("a", "annotator_a"):
        return "annotator_A"
    if norm in ("b", "annotator_b"):
        return "annotator_B"
    raise argparse.ArgumentTypeError(
        f"Invalid annotator '{val}'. Must be 'A', 'B', 'annotator_A', or 'annotator_B'."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ARGUMAP Human Annotation Workspace for UK Hansard AI debate pilot."
    )
    parser.add_argument(
        "--annotator",
        "-a",
        type=parse_annotator_arg,
        required=True,
        help="Target annotator session ('A' or 'B')",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=8765,
        help="Port to bind the local web interface (default: 8765)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host address to bind (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print current session status and exit",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate current session state and exit",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Attempt export of completed package and exit",
    )

    args = parser.parse_args()
    ann_id = args.annotator

    session = WorkspaceSession(annotator_id=ann_id)

    # CLI command: --status
    if args.status:
        summary = session.get_summary()
        print(f"=== ARGUMAP Workspace Status: {ann_id} ===")
        print(f"Status: {summary['status']}")
        print(f"Units Labeled: {summary['labeled_units']}/{summary['total_units']} ({summary['unit_progress_pct']}%)")
        print(f"Relations Labeled: {summary['labeled_relations']}/{summary['total_relations']} ({summary['relation_progress_pct']}%)")
        print(f"Overall Progress: {summary['labeled_items']}/{summary['total_items']} ({summary['total_progress_pct']}%)")
        print(f"Complete: {'YES' if summary['is_complete'] else 'NO'}")
        print(f"Working File: {summary['working_file']}")
        return 0

    # CLI command: --validate
    if args.validate:
        val = session.validate_session()
        print(f"=== Validating Working State: {ann_id} ===")
        print(f"Syntax Valid: {val['syntax_valid']}")
        print(f"Complete: {val['is_complete']}")
        print(f"Production Valid: {val['production_valid']}")
        if val["syntax_errors"]:
            print(f"Syntax Errors ({len(val['syntax_errors'])}):")
            for e in val["syntax_errors"]:
                print(f"  [ERROR] {e}")
        if val["missing_items"]:
            print(f"Unannotated Items ({len(val['missing_items'])}):")
            for m in val["missing_items"][:10]:
                print(f"  [MISSING] {m}")
            if len(val["missing_items"]) > 10:
                print(f"  ... and {len(val['missing_items']) - 10} more.")
        return 0 if val["syntax_valid"] else 1

    # CLI command: --export
    if args.export:
        success, msg, path = session.export_completed_package()
        if success:
            print(f"[SUCCESS] {msg}")
            return 0
        else:
            print(f"[FAILED] {msg}")
            return 1

    # Web Server Mode
    print(f"\n=======================================================")
    print(f"  ARGUMAP Human Annotation Workspace: {ann_id}")
    print(f"=======================================================")
    print(f"  • Template File: {session.template_path}")
    print(f"  • Working Copy:  {session.working_path}")
    print(f"  • URL:           http://{args.host}:{args.port}/")
    print(f"  • Press Ctrl+C to stop the server.")
    print(f"=======================================================\n")

    app = create_annotation_app(ann_id)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
