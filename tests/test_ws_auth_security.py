import json, uuid, pytest
from core.auth_cookie_config import ACCESS_COOKIE_NAME
from core.provisioning_context import provisioning_channel
from security import create_access_token, hash_password
import models

def _user(db):
    email=f"ws.{uuid.uuid4().hex[:8]}@t.gn"
    with provisioning_channel("test_fixture"):
        u=models.User(email=email, hashed_password=hash_password("StrongPass12!"), role="receptionist", is_active=True)
        db.add(u); db.commit(); db.refresh(u)
    return u

def _tok(u):
    return create_access_token({"sub":u.email,"user_id":u.id,"user_role":u.role,"role":u.role})

def test_health(client):
    with client.websocket_connect("/ws/health") as ws:
        assert ws.receive_json()["type"]=="ready"

def test_reject_query(client, db_session):
    u=_user(db_session)
    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/live?token={_tok(u)}") as ws: ws.receive_json()

def test_cookie(client, db_session):
    u=_user(db_session); t=_tok(u)
    with client.websocket_connect("/ws/live", cookies={ACCESS_COOKIE_NAME:t}) as ws:
        m=ws.receive_json(); assert m["type"]=="connected" and m["user_id"]==u.id

def test_auth_msg(client, db_session):
    u=_user(db_session); t=_tok(u)
    with client.websocket_connect("/ws/live") as ws:
        assert ws.receive_json()["type"]=="auth_required"
        ws.send_text(json.dumps({"type":"auth","token":t}))
        assert ws.receive_json()["type"]=="connected"
