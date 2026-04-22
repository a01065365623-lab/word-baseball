"""
로비 소켓 이벤트
----------------
action:create_room  → 룸 생성
action:join_room    → 룸 입장
action:leave_room   → 룸 퇴장
"""

from flask import request, session
from flask_socketio import join_room, leave_room, emit
from ..extensions import socketio
from ..game.room_manager import room_manager


@socketio.on("action:create_room")
def on_create_room(data):
    username = (data or {}).get("username") or session.get("username") or "Guest"
    code = room_manager.create_room(request.sid, username)
    join_room(code)
    emit("state:room_created", {"code": code, "username": username})
    emit("state:room_update", {
        "code": code,
        "players": room_manager.get_players(code),
    }, to=code)


@socketio.on("action:join_room")
def on_join_room(data):
    data = data or {}
    code = (data.get("code") or "").upper().strip()
    username = data.get("username") or session.get("username") or "Guest"

    ok = room_manager.join_room(code, request.sid, username)
    if not ok:
        emit("state:error", {"message": "방을 찾을 수 없거나 이미 가득 찼습니다"})
        return

    join_room(code)
    emit("state:room_joined", {"code": code, "username": username})
    emit("state:room_update", {
        "code": code,
        "players": room_manager.get_players(code),
    }, to=code)


@socketio.on("action:leave_room")
def on_leave_room(data):
    code = room_manager.find_room_by_sid(request.sid)
    if code:
        room_manager.leave_room(request.sid)
        leave_room(code)
        emit("state:room_update", {
            "code": code,
            "players": room_manager.get_players(code),
        }, to=code)


@socketio.on("disconnect")
def on_disconnect():
    code = room_manager.find_room_by_sid(request.sid)
    if code:
        room_manager.leave_room(request.sid)
        emit("state:room_update", {
            "code": code,
            "players": room_manager.get_players(code),
        }, to=code)
