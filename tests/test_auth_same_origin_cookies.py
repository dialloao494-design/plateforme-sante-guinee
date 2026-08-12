import uuid, models
from core.auth_cookie_config import ACCESS_COOKIE_NAME
from core.provisioning_context import provisioning_channel
from security import hash_password

def test_cookie_login(client, db_session, monkeypatch):
    monkeypatch.setenv("AUTH_JSON_TOKENS","false")
    email=f"c.{uuid.uuid4().hex[:8]}@t.gn"
    with provisioning_channel("test_fixture"):
        db_session.add(models.User(email=email, hashed_password=hash_password("StrongPass12!"), role="receptionist", is_active=True)); db_session.commit()
    r=client.post("/auth/login-json", json={"email":email,"password":"StrongPass12!"})
    assert r.status_code==200 and r.json().get("access_token") is None and r.cookies.get(ACCESS_COOKIE_NAME)

def test_cookie_me(client, db_session, monkeypatch):
    monkeypatch.setenv("AUTH_JSON_TOKENS","false")
    email=f"m.{uuid.uuid4().hex[:8]}@t.gn"
    with provisioning_channel("test_fixture"):
        db_session.add(models.User(email=email, hashed_password=hash_password("StrongPass12!"), role="receptionist", is_active=True)); db_session.commit()
    login=client.post("/auth/login-json", json={"email":email,"password":"StrongPass12!"})
    me=client.get("/auth/me", cookies=login.cookies)
    assert me.status_code==200 and me.json()["email"]==email
