"""Isolated live Gemini pilot. Run explicitly with: python api/scripts/verify_ai_pilot.py --live"""

import argparse
import io
import json
import os
import sys
import tempfile
import time
from datetime import date, datetime, timedelta, timezone

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from api.app.config import settings
from api.app.database import Base, get_db
from api.app.main import app
from api.app.models.entities import Campaign, Case, Claim, Class, ClassMember, Criterion, User
from api.app.security import hash_password
from api.app.review.gemini_read import GeminiReadProvider
from api.app.review.gemini_transparency import GeminiTransparencyProvider
from api.app.services.template_service import CRITERIA_49K14_1_DEFINITIONS


def _synthetic_certificate() -> bytes:
    image = Image.new("RGB", (1500, 900), "#fffdf7")
    draw = ImageDraw.Draw(image)
    regular = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 35)
    title = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 54)
    warning = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 42)
    draw.rectangle((24, 24, 1476, 876), outline="#1f3a5f", width=8)
    draw.text((125, 105), "CHỨNG NHẬN THAM GIA — MẪU KIỂM THỬ", font=title, fill="#123456")
    lines = [
        "Đơn vị ghi trên mẫu: Trung tâm Tình nguyện Cộng đồng Giả lập",
        "Người nhận: Nguyễn Văn A",
        "Hoạt động: Quyên góp hỗ trợ cộng đồng ngoài trường",
        "Ngày hoạt động: 15/10/2026",
        "Mã trên mẫu: DEMO-001 (không tra cứu được)",
    ]
    for index, line in enumerate(lines):
        draw.text((125, 260 + index * 75), line, font=regular, fill="#152b42")
    draw.text((125, 730), "GIẢ LẬP — KHÔNG HỢP LỆ ĐỂ CHẤM ĐIỂM", font=warning, fill="#b42318")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _expect(response, expected_status: int, label: str) -> dict:
    if response.status_code != expected_status:
        raise RuntimeError(f"{label}: HTTP {response.status_code}: {response.text[:500]}")
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="One isolated Gemini pilot using synthetic evidence")
    parser.add_argument("--live", action="store_true", help="Allow the two paid Gemini generateContent calls")
    parser.add_argument("--stub-models", action="store_true", help="Verify the API flow with fixed model outputs")
    args = parser.parse_args()
    if not args.live and not args.stub_models:
        parser.error("Choose --live or --stub-models")
    if args.live and not settings.GEMINI_API_KEY:
        parser.error("GEMINI_API_KEY is missing from the local .env")

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False)
    db = session_factory()
    saved_settings = {name: getattr(settings, name) for name in (
        "AI_READ_ENABLED", "AI_TRANSPARENCY_ENABLED", "STORAGE_BACKEND", "STORAGE_DIR", "CRON_SECRET",
        "GEMINI_API_KEY",
    )}

    original_read = GeminiReadProvider.read
    original_assess = GeminiTransparencyProvider.assess
    if args.stub_models:
        settings.GEMINI_API_KEY = "pilot-stub-key"

        async def stub_read(self, evidence_file_id, sha256, mime_type, data):
            return {"evidence_file_id": evidence_file_id, "sha256": sha256, "readable": True,
                    "unreadable_reason": "", "facts": [
                        {"kind": "activity_name", "value": "Quyên góp hỗ trợ cộng đồng ngoài trường",
                         "page": 1, "source_excerpt": "Quyên góp hỗ trợ cộng đồng ngoài trường"},
                        {"kind": "event_date", "value": "15/10/2026", "page": 1,
                         "source_excerpt": "Ngày hoạt động: 15/10/2026"},
                    ]}

        async def stub_assess(self, **kwargs):
            return {"evidence_file_id": kwargs["evidence_file_id"], "sha256": kwargs["sha256"],
                    "criterion_code": kwargs["criterion"]["code"],
                    "rule_clause_id": kwargs["criterion"]["clause_id"],
                    "rule_text": kwargs["criterion"]["description"],
                    "evidence_requirements": kwargs["criterion"]["evidence_notes"],
                    "verdict": "FLAGGED", "reason": "Ảnh ghi rõ là mẫu giả lập không dùng để chấm điểm.",
                    "citations": [{"page": 1, "source_excerpt": "Quyên góp hỗ trợ cộng đồng ngoài trường",
                                   "kind": "activity_name", "value": "Quyên góp hỗ trợ cộng đồng ngoài trường"}],
                    "visual_signals": [{"page": 1, "description": "Ghi rõ GIẢ LẬP", "concern": True}],
                    "authenticity": "SUSPICIOUS", "limitations": ["Chưa xác minh nguồn cấp."],
                    "requires_human_review": True, "model": self.model,
                    "prompt_version": "ai-transparency-v1"}

        GeminiReadProvider.read = stub_read
        GeminiTransparencyProvider.assess = stub_assess

    with tempfile.TemporaryDirectory(prefix="ai-drl-pilot-") as temp_dir:
        settings.AI_READ_ENABLED = True
        settings.AI_TRANSPARENCY_ENABLED = True
        settings.STORAGE_BACKEND = "local"
        settings.STORAGE_DIR = temp_dir
        settings.CRON_SECRET = "isolated-pilot-tick"
        now = datetime.now(timezone.utc)
        password = "PilotOnly_2026!"
        classroom = Class(code="PILOT-ONLY", name="Lớp thử AI biệt lập")
        student = User(username="pilot_student", password_hash=hash_password(password),
                       full_name="Nguyễn Văn A", role="STUDENT", is_active=True)
        bcs = User(username="pilot_bcs", password_hash=hash_password(password),
                   full_name="Ban cán sự thử", role="BCS", is_active=True)
        db.add_all([classroom, student, bcs])
        db.flush()
        db.add_all([
            ClassMember(class_id=classroom.id, user_id=student.id, member_role="STUDENT"),
            ClassMember(class_id=classroom.id, user_id=bcs.id, member_role="BCS"),
        ])
        campaign = Campaign(
            class_id=classroom.id, title="Đợt thử AI tách biệt", term="HK1-2026",
            term_start_on=date(2026, 9, 1), term_end_on=date(2026, 12, 31),
            status="OPEN", template_code="49K14_1_V1",
            open_at=now - timedelta(days=1), submission_deadline_at=now + timedelta(days=7),
        )
        db.add(campaign)
        db.flush()
        source = next(item for item in CRITERIA_49K14_1_DEFINITIONS if item["code"] == "7b")
        criterion = Criterion(
            campaign_id=campaign.id, code=source["code"], section_code=source["section_code"],
            section_title=source["section_title"], section_max_score=source["section_max_score"],
            title=source["title"], description=source["description"], max_score=source["max_score"],
            requires_evidence=source["requires_evidence"], evidence_notes=source["evidence_notes"],
            allowed_input_roles=source["allowed_input_roles"], rule_config=source["rule_config"],
            sort_order=source["sort_order"],
        )
        case = Case(campaign_id=campaign.id, student_id=student.id, status="DRAFT", version=1)
        db.add_all([criterion, case])
        db.flush()
        claim = Claim(case_id=case.id, criterion_id=criterion.id)
        db.add(claim)
        db.commit()

        def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        started = time.monotonic()
        try:
            with TestClient(app) as client:
                student_auth = _expect(client.post("/api/v1/auth/login", json={"username": student.username,
                                                                               "password": password}), 200, "student login")
                student_headers = {"X-CSRF-Token": student_auth["csrf_token"]}
                update = _expect(client.put(f"/api/v1/student/cases/{case.id}/claims/{criterion.id}",
                                            json={"self_score": "1.00", "student_note": "Mẫu kiểm thử",
                                                  "expected_version": 1}, headers=student_headers), 200, "self score")
                upload = _expect(client.post(f"/api/v1/student/cases/{case.id}/evidence",
                                             data={"criterion_id": criterion.id},
                                             files={"file": ("pilot-demo.png", _synthetic_certificate(), "image/png")},
                                             headers=student_headers), 201, "evidence upload")
                submitted = _expect(client.post(f"/api/v1/student/cases/{case.id}/submit",
                                                json={"expected_version": update["version"]},
                                                headers=student_headers), 200, "case submit")
                bcs_auth = _expect(client.post("/api/v1/auth/login", json={"username": bcs.username,
                                                                           "password": password}), 200, "BCS login")
                bcs_headers = {"X-CSRF-Token": bcs_auth["csrf_token"]}
                run = _expect(client.post(f"/api/v1/bcs/cases/{case.id}/ai-reviews",
                                          headers=bcs_headers), 202, "queue")
                print("API flow: student score -> upload -> submit -> BCS queue: OK", flush=True)
                print(f"Queued case status={submitted['status']}, run status={run['status']}", flush=True)
                tick = _expect(client.post("/api/v1/internal/ai-tick",
                                           headers={"Authorization": f"Bearer {settings.CRON_SECRET}"}), 200, "worker")
                latest = _expect(client.get(f"/api/v1/bcs/cases/{case.id}/ai-reviews/latest"), 200, "latest")["run"]
                suggestions = _expect(client.get(f"/api/v1/bcs/cases/{case.id}/score-suggestions"),
                                      200, "score suggestions")
                steps = {step["kind"]: step for step in latest["steps"]}
                read_files = (steps["AI_READ"]["output"] or {}).get("files", [])
                assessments = (steps["AI_TRANSPARENCY"]["output"] or {}).get("assessments", [])
                db.refresh(case)
                db.refresh(claim)
                report = {
                    "synthetic_only": True,
                    "model_calls": "STUBBED" if args.stub_models else "LIVE",
                    "api_flow": "OK",
                    "elapsed_seconds": round(time.monotonic() - started, 1),
                    "models": {"read": settings.GEMINI_MODEL, "transparency": settings.GEMINI_TRANSPARENCY_MODEL},
                    "tick": tick,
                    "run_status": latest["status"], "run_error": latest["error_code"],
                    "step_statuses": {key: {"status": value["status"], "error_code": value["error_code"]}
                                      for key, value in steps.items()},
                    "readable": read_files[0]["readable"] if read_files else None,
                    "fact_kinds": [fact["kind"] for fact in read_files[0]["facts"]] if read_files else [],
                    "read_facts": [{"kind": fact["kind"], "value": fact["value"], "page": fact["page"]}
                                   for fact in read_files[0]["facts"]] if read_files else [],
                    "verdict": assessments[0]["verdict"] if assessments else None,
                    "reason": assessments[0]["reason"] if assessments else None,
                    "citation_count": len(assessments[0]["citations"]) if assessments else 0,
                    "draft_score": suggestions["items"][0]["draft_score"],
                    "requires_bcs_approval": suggestions["requires_bcs_approval"],
                    "case_status_after_worker": case.status,
                    "approved_score_after_worker": str(claim.approved_score) if claim.approved_score is not None else None,
                    "expected_demo_handling": "FLAGGED or UNKNOWN",
                }
                print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
                if latest["status"] != "NEEDS_HUMAN":
                    print("Pilot incomplete: the model step is queued for retry; BCS data is unchanged.", flush=True)
                    raise SystemExit(2)
                if case.status != "BCS_REVIEW" or claim.approved_score is not None:
                    raise RuntimeError("AI changed a BCS decision field")
                if args.stub_models and (report["verdict"] != "FLAGGED" or report["draft_score"] is not None):
                    raise RuntimeError("Flagged evidence was allowed into a score suggestion")
        finally:
            app.dependency_overrides.pop(get_db, None)
            GeminiReadProvider.read = original_read
            GeminiTransparencyProvider.assess = original_assess
            for name, value in saved_settings.items():
                setattr(settings, name, value)
            db.close()
            engine.dispose()


if __name__ == "__main__":
    main()
