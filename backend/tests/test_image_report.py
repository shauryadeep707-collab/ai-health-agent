import io
import uuid
import pytest
from pathlib import Path
from backend.app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_universal_image_report_upload_and_viewer(client):
    # 1. Register and get token
    email = f"report.test.{uuid.uuid4().hex[:8]}@example.com"
    pwd = "SecurePassword123#"
    reg_res = client.post("/api/auth/patient/register", json={
        "full_name": "Report Test User",
        "email": email,
        "phone": "+919876543210",
        "password": pwd,
        "gender": "MALE",
        "blood_group": "B+",
        "consent_health": True,
        "consent_privacy": True
    })
    assert reg_res.status_code == 201
    token = reg_res.get_json()["token"]

    # 2. Path to user's real uploaded Himalayan Hospital report image
    img_path = Path(r"C:\Users\shaur\.gemini\antigravity\brain\e66f2c19-3152-45c2-af40-cd4faa3abf96\.user_uploaded\media_1792928113622_f6c6dd45.jpg")
    assert img_path.exists(), "Test image artifact must exist"

    with open(img_path, "rb") as f:
        img_bytes = f.read()

    upload_data = {
        "file": (io.BytesIO(img_bytes), "WhatsApp_Image_2026-10-25_at_12.44.58_PM.jpeg", "image/jpeg"),
        "test_type": ""  # empty so auto-detection takes over
    }

    # 3. Post upload
    res = client.post(
        "/api/patient/reports/upload",
        data=upload_data,
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 201, f"Upload failed: {res.get_json()}"
    data = res.get_json()
    assert data["success"] is True
    report_id = data["report_id"]

    # 4. Check auto-detected title is NOT the raw filename
    assert "whatsapp" not in data["test_type"].lower(), f"Test type should not be raw filename, got: {data['test_type']}"
    assert "urine" in data["test_type"].lower() or "pathology" in data["test_type"].lower() or "report" in data["test_type"].lower()

    # 5. Check clinical parameters were detected and extracted
    values = data["test_values"]
    assert len(values) >= 3, f"Expected lab parameters to be extracted, got: {len(values)}"
    param_names = [v["parameter_name"].lower() for v in values]
    # Check for urine parameters
    assert any("pus" in p or "protein" in p or "ph" in p or "gravity" in p or "nitrite" in p for p in param_names), f"Urine parameters missing: {param_names}"

    # 6. Test original image file viewing endpoint
    file_res = client.get(f"/api/patient/reports/{report_id}/file", headers={"Authorization": f"Bearer {token}"})
    assert file_res.status_code == 200
    assert file_res.content_type.startswith("image/")
    assert len(file_res.data) == len(img_bytes)

    # 7. Test token query parameter for image tags
    query_file_res = client.get(f"/api/patient/reports/{report_id}/file?token={token}")
    assert query_file_res.status_code == 200
    assert query_file_res.content_type.startswith("image/")
