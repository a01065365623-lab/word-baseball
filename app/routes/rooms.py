from flask import Blueprint, jsonify, session
from ..game.room_manager import room_manager

rooms_bp = Blueprint("rooms", __name__)


@rooms_bp.get("/")
def list_rooms():
    """대기 중인 룸 목록 반환."""
    return jsonify({"rooms": room_manager.list_waiting_rooms()})


@rooms_bp.post("/")
def create_room():
    """룸 생성 (소켓 연결 전 코드 발급용 — 실제 입장은 소켓 이벤트로)."""
    username = session.get("username") or "Guest"
    # 임시 sid 없이 코드만 예약 (소켓 join_room 시 덮어씀)
    code = room_manager._unique_code()
    return jsonify({"code": code})
