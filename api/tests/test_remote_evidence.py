from api.app.config import settings
from api.app.routes import files, student
from api.tests.conftest import login_helper


def test_direct_upload_is_bound_to_student_case_and_verified(client, seed_data, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "supabase")
    monkeypatch.setattr(student, "create_upload_url", lambda key: f"https://storage.example/{key}")
    monkeypatch.setattr(student, "download_object", lambda key: b"%PDF-1.4 valid pdf")
    monkeypatch.setattr(files, "create_download_url", lambda key: f"https://storage.example/download/{key}")

    owner = login_helper(client, "sv001")
    other = login_helper(client, "sv002")
    case = seed_data["cases"][0]
    criterion = seed_data["criteria"][0]
    endpoint = f"/api/v1/student/cases/{case.id}/evidence"

    oversized = client.post(
        endpoint + "/upload-ticket",
        json={"criterion_id": criterion.id, "filename": "proof.pdf", "mime_type": "application/pdf", "size_bytes": 10 * 1024 * 1024 + 1},
        cookies=owner["cookies"], headers=owner["headers"],
    )
    assert oversized.status_code == 422
    assert oversized.json()["error"]["code"] == "FILE_TOO_LARGE"

    reservation = client.post(
        endpoint + "/upload-ticket",
        json={"criterion_id": criterion.id, "filename": "proof.pdf", "mime_type": "application/pdf", "size_bytes": len(b"%PDF-1.4 valid pdf")},
        cookies=owner["cookies"], headers=owner["headers"],
    )
    assert reservation.status_code == 200
    ticket = reservation.json()["ticket"]

    forbidden = client.post(endpoint + "/complete", json={"ticket": ticket}, cookies=other["cookies"], headers=other["headers"])
    assert forbidden.status_code == 403

    tampered = client.post(endpoint + "/complete", json={"ticket": ticket + "x"}, cookies=owner["cookies"], headers=owner["headers"])
    assert tampered.status_code == 400

    complete = client.post(endpoint + "/complete", json={"ticket": ticket}, cookies=owner["cookies"], headers=owner["headers"])
    assert complete.status_code == 201
    file_id = complete.json()["id"]
    assert complete.json()["size_bytes"] == len(b"%PDF-1.4 valid pdf")

    repeated = client.post(endpoint + "/complete", json={"ticket": ticket}, cookies=owner["cookies"], headers=owner["headers"])
    assert repeated.status_code == 409

    owner_read = client.get(f"/api/v1/files/{file_id}", cookies=owner["cookies"], follow_redirects=False)
    assert owner_read.status_code == 307
    assert owner_read.headers["location"].startswith("https://storage.example/download/")

    other_read = client.get(f"/api/v1/files/{file_id}", cookies=other["cookies"], follow_redirects=False)
    assert other_read.status_code == 403


def test_direct_upload_rejects_file_content_mismatch(client, seed_data, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "supabase")
    monkeypatch.setattr(student, "create_upload_url", lambda key: f"https://storage.example/{key}")
    monkeypatch.setattr(student, "download_object", lambda key: b"not really a PDF")
    owner = login_helper(client, "sv001")
    case = seed_data["cases"][0]
    criterion = seed_data["criteria"][0]
    endpoint = f"/api/v1/student/cases/{case.id}/evidence"

    reservation = client.post(
        endpoint + "/upload-ticket",
        json={"criterion_id": criterion.id, "filename": "fake.pdf", "mime_type": "application/pdf", "size_bytes": len(b"not really a PDF")},
        cookies=owner["cookies"], headers=owner["headers"],
    )
    assert reservation.status_code == 200
    complete = client.post(endpoint + "/complete", json={"ticket": reservation.json()["ticket"]}, cookies=owner["cookies"], headers=owner["headers"])
    assert complete.status_code == 422
    assert complete.json()["error"]["code"] == "INVALID_FILE_TYPE"
