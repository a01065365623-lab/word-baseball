"""
게임 소켓 이벤트
----------------
action:ready         → 준비 완료
action:answer        → 단어 정답 제출
action:request_word  → 다음 단어 요청 (디버그용)
"""

from flask import request, session
from flask_socketio import emit
from ..extensions import socketio
from ..game.room_manager import room_manager
from ..game.word_engine import word_engine
from ..game.baseball import HOMERUN, TRIPLE


def _emit_game_state(code: str, extra: dict = None):
    game = room_manager.get_game(code)
    if not game:
        return
    payload = game.to_dict()
    if extra:
        payload.update(extra)
    emit("state:game_update", payload, to=code)


def _next_word(code: str, difficulty: int = 1):
    """새 단어를 출제하고 룸에 브로드캐스트."""
    word = word_engine.get_random_word(difficulty)
    if not word:
        emit("state:error", {"message": "단어 데이터가 없습니다"}, to=code)
        return
    # meaning 은 서버에만 보관
    room_manager.set_current_word(code, word)
    # 클라이언트에는 word(영단어) + difficulty 만 전송
    emit("state:new_word", {
        "word": word["word"],
        "difficulty": word.get("difficulty", 1),
        "category": word.get("category", "general"),
    }, to=code)


@socketio.on("action:ready")
def on_ready(data):
    code = room_manager.find_room_by_sid(request.sid)
    if not code:
        return
    both_ready = room_manager.set_ready(code, request.sid)
    emit("state:player_ready", {"sid": request.sid}, to=code)

    if both_ready:
        room_manager.start_game(code)
        emit("state:game_start", {
            "players": room_manager.get_players(code),
        }, to=code)
        _next_word(code, difficulty=1)


@socketio.on("action:answer")
def on_answer(data):
    data = data or {}
    code = room_manager.find_room_by_sid(request.sid)
    if not code:
        return

    game = room_manager.get_game(code)
    current_word = room_manager.get_current_word(code)
    if not game or not current_word or game.game_over:
        return

    user_answer = (data.get("answer") or "").strip()
    word_str = current_word["word"]
    difficulty = current_word.get("difficulty", 1)

    result_type = word_engine.check_answer(word_str, user_answer, difficulty)

    if result_type == "strike":
        event_result = game.strike()
    else:
        # difficulty 3(고급): 남은 시간 7초 이상이면 홈런, 미만이면 3루타
        if difficulty == 3 and result_type != "strike":
            time_left = int(data.get("time_left") or 0)
            result_type = HOMERUN if time_left >= 7 else TRIPLE
        event_result = game.hit(result_type)

    # 정답 공개 (이벤트 결과에 포함)
    event_result["correct_answer"] = current_word.get("meaning", "")
    event_result["word"] = word_str
    event_result["submitted_by"] = request.sid

    emit("state:answer_result", event_result, to=code)

    if game.game_over:
        _save_result(code)
        emit("state:game_over", {
            "score": game.score,
            "winner": game.winner,
            "players": room_manager.get_players(code),
        }, to=code)
    else:
        # 이닝 전환 시 or 아웃/히트 후 다음 단어
        _next_word(code, difficulty=difficulty)


@socketio.on("action:request_word")
def on_request_word(data):
    """디버그·재시작용 — 다음 단어 강제 요청."""
    code = room_manager.find_room_by_sid(request.sid)
    if code:
        _next_word(code)


@socketio.on("action:use_item")
def on_use_item(data):
    data = data or {}
    code = room_manager.find_room_by_sid(request.sid)
    if not code:
        return
    item_type = data.get("type")

    if item_type == "swap":
        current_word = room_manager.get_current_word(code)
        difficulty = current_word.get("difficulty", 1) if current_word else 1
        _next_word(code, difficulty)

    elif item_type == "sabotage":
        emit("state:item_used", {
            "type": "sabotage",
            "by_sid": request.sid,
            "penalty": data.get("penalty", 5),
        }, to=code)


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

def _save_result(code: str):
    """게임 종료 시 DB에 룸 상태 저장."""
    try:
        from ..extensions import db
        from ..models.room import Room
        room_record = Room.query.filter_by(code=code).first()
        if room_record:
            room_record.status = "finished"
            db.session.commit()
    except Exception:
        pass
