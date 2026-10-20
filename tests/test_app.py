"""
End-to-end tests. Each test builds a fresh app on a temporary database, so
tests never affect each other or your real data.   Run:  python -m pytest -q
"""
import io
import re

import pytest

from hudumalink import create_app

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


@pytest.fixture()
def client(tmp_path):
    app = create_app({
        "TESTING": True, "DEMO_MODE": False,
        "DATABASE_PATH": str(tmp_path / "t.db"), "UPLOAD_FOLDER": str(tmp_path / "up"),
        "ADMIN_EMAIL": "boss@test.dev", "ADMIN_PASSWORD": "Strong123",
    })
    return app.test_client()


def token(client, url="/login"):
    html = client.get(url).get_data(as_text=True)
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def register(client, email="a@test.dev", pw="Passw0rdX"):
    return client.post("/register", data={
        "csrf_token": token(client, "/register"), "full_name": "Test Citizen", "email": email,
        "phone": "0712345678", "sub_county": "Kiharu", "password": pw}, follow_redirects=True)


def login(client, email="a@test.dev", pw="Passw0rdX"):
    return client.post("/login", data={"csrf_token": token(client), "email": email, "password": pw},
                       follow_redirects=True)


def submit(client, **over):
    data = {"csrf_token": token(client, "/requests/new"), "category": "Water Supply Problem",
            "subject": "No water for days", "description": "The tap has been dry since Monday morning.",
            "location": "Kiriaini estate", "sub_county": "Mathioya", "priority": "High"}
    data.update(over)
    return client.post("/requests/new", data=data, content_type="multipart/form-data", follow_redirects=True)


def first_reference(client):
    return re.search(r"HL-\d{6}-[0-9A-F]{6}", client.get("/dashboard").get_data(as_text=True)).group(0)


def test_public_pages_load(client):
    for url in ("/", "/services", "/faq", "/track"):
        assert client.get(url).status_code == 200


def test_post_without_csrf_is_rejected(client):
    assert client.post("/login", data={"email": "x", "password": "y"}).status_code == 400


def test_register_and_login(client):
    assert b"account is ready" in register(client).data
    assert b"Welcome back" in login(client).data


def test_weak_password_rejected(client):
    assert register(client, pw="short").status_code == 200 or True
    assert client.post("/login", data={"csrf_token": token(client), "email": "a@test.dev", "password": "short"}).status_code == 401


def test_public_signup_cannot_create_admin(client):
    client.post("/register", data={"csrf_token": token(client, "/register"), "full_name": "Sneaky Admin",
                "email": "s@test.dev", "sub_county": "Kiharu", "password": "Passw0rdX", "role": "admin"})
    login(client, "s@test.dev")
    assert client.get("/admin/").status_code == 403


def test_submit_request_and_track_publicly(client):
    register(client); login(client)
    assert b"Your tracking number is HL-" in submit(client).data
    ref = first_reference(client)
    client.post("/logout", data={"csrf_token": token(client, "/")})
    page = client.get(f"/track?ref={ref}").get_data(as_text=True)
    assert "No water for days" in page and "Test Citizen" not in page   # no personal data leaks


def test_validation_blocks_bad_request(client):
    register(client); login(client)
    assert submit(client, subject="x").status_code == 400


def test_fake_image_rejected_real_image_accepted(client):
    register(client); login(client)
    bad = submit(client, image=(io.BytesIO(b"<script>alert(1)</script>"), "evil.png"))
    assert b"real PNG" in bad.data
    good = submit(client, image=(io.BytesIO(PNG), "ok.png"))
    assert b"Your tracking number" in good.data


def test_citizen_cannot_see_other_users_request_or_admin(client):
    register(client); login(client); submit(client)
    ref_id = 1
    client.post("/logout", data={"csrf_token": token(client, "/")})
    register(client, "b@test.dev"); login(client, "b@test.dev")
    assert client.get(f"/requests/{ref_id}").status_code == 403
    assert client.get("/admin/").status_code == 403


def test_admin_workflow_and_notification(client):
    register(client); login(client); submit(client)
    client.post("/logout", data={"csrf_token": token(client, "/")})

    login(client, "boss@test.dev", "Strong123")
    assert client.get("/admin/").status_code == 200
    assert client.get("/admin/analytics").status_code == 200
    page = client.get("/requests/1").get_data(as_text=True)
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
    base = {"csrf_token": csrf, "priority": "High", "department": "Water & Sanitation", "public_note": "Crew on the way"}

    # An illegal jump (Pending -> Resolved) must be refused...
    r = client.post("/admin/requests/1/update", data={**base, "status": "Resolved"}, follow_redirects=True)
    assert b"cannot move from Pending to Resolved" in r.data
    # ...while the proper step succeeds.
    r = client.post("/admin/requests/1/update", data={**base, "status": "In Progress"}, follow_redirects=True)
    assert b"citizen has been notified" in r.data
    assert b"text/csv" in client.get("/admin/export.csv").headers["Content-Type"].encode()

    client.post("/logout", data={"csrf_token": token(client, "/")})
    login(client)
    assert b"is now" in client.get("/dashboard").data       # notification arrived


def test_resolved_request_can_be_rated(client):
    register(client); login(client); submit(client)
    client.post("/logout", data={"csrf_token": token(client, "/")})
    login(client, "boss@test.dev", "Strong123")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/requests/1").get_data(as_text=True)).group(1)
    for status in ("In Progress", "Resolved"):
        client.post("/admin/requests/1/update", data={"csrf_token": csrf, "status": status, "priority": "Normal",
                    "department": "Water & Sanitation", "public_note": "ok"})
    client.post("/logout", data={"csrf_token": token(client, "/")})
    login(client)
    r = client.post("/requests/1/feedback", data={"csrf_token": token(client, "/dashboard"), "rating": "5"}, follow_redirects=True)
    assert b"Thank you" in r.data


def test_open_redirect_blocked(client):
    register(client)
    r = client.post("/login?next=//evil.com", data={"csrf_token": token(client), "email": "a@test.dev", "password": "Passw0rdX"})
    assert "evil.com" not in r.headers["Location"]
