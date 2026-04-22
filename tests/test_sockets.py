"""
소켓 통합 테스트 — Flask test_client + flask_socketio test mode 사용.
"""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app
from app.extensions import socketio as _socketio


@pytest.fixture
def app():
    application = create_app("development")
    application.config["TESTING"] = True
    application.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with application.app_context():
        from app.extensions import db
        db.create_all()
    yield application


@pytest.fixture
def client(app):
    return _socketio.test_client(app, flask_test_client=app.test_client())


def test_connect(client):
    assert client.is_connected()


def test_create_and_join_room(app):
    client1 = _socketio.test_client(app, flask_test_client=app.test_client())
    client2 = _socketio.test_client(app, flask_test_client=app.test_client())

    # 룸 생성
    client1.emit("action:create_room", {"username": "Alice"})
    received1 = client1.get_received()
    create_event = next(
        (e for e in received1 if e["name"] == "state:room_created"), None
    )
    assert create_event is not None
    code = create_event["args"][0]["code"]
    assert len(code) == 6

    # 룸 입장
    client2.emit("action:join_room", {"code": code, "username": "Bob"})
    received2 = client2.get_received()
    join_event = next(
        (e for e in received2 if e["name"] == "state:room_joined"), None
    )
    assert join_event is not None


def test_join_nonexistent_room(app):
    client = _socketio.test_client(app, flask_test_client=app.test_client())
    client.emit("action:join_room", {"code": "XXXXXX", "username": "Ghost"})
    received = client.get_received()
    error_event = next(
        (e for e in received if e["name"] == "state:error"), None
    )
    assert error_event is not None


def test_ready_starts_game(app):
    client1 = _socketio.test_client(app, flask_test_client=app.test_client())
    client2 = _socketio.test_client(app, flask_test_client=app.test_client())

    client1.emit("action:create_room", {"username": "Alice"})
    code = client1.get_received()[-1]["args"][0]["code"]

    client2.emit("action:join_room", {"code": code, "username": "Bob"})
    client2.get_received()  # flush

    client1.emit("action:ready", {})
    client2.emit("action:ready", {})

    # 양쪽 모두 준비 → game_start 이벤트 수신 확인
    all_events = client1.get_received() + client2.get_received()
    start_event = next(
        (e for e in all_events if e["name"] == "state:game_start"), None
    )
    assert start_event is not None
