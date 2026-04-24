import os
import sqlite3
import random

from flask import Flask, g, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=os.path.join(_BASE_DIR, 'app', 'static'), static_url_path='')
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')

socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

DATABASE = os.path.join(_BASE_DIR, 'words.db')

VALID_LANGS = {
    'en', 'ko', 'ja', 'zh', 'de', 'fr', 'hi', 'es', 'pt', 'it', 'ru', 'tr', 'vi', 'ar'
}


# ── DB 연결 (REST 라우트용) ───────────────────────────────────

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def _db_word(difficulty: int, hint_lang: str = 'ko', answer_lang: str = 'en') -> dict | None:
    """소켓 핸들러용 단어 조회 — 독립 커넥션 사용."""
    if hint_lang not in VALID_LANGS:
        hint_lang = 'ko'
    if answer_lang not in VALID_LANGS:
        answer_lang = 'en'
    # hint_lang == answer_lang 이면 hint 를 영어로 fallback
    effective_hint = hint_lang if hint_lang != answer_lang else 'en'
    if effective_hint == answer_lang:
        effective_hint = 'ko'
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            f'SELECT {answer_lang}, {effective_hint}, level FROM vocabulary'
            f' WHERE level = ? AND {answer_lang} IS NOT NULL AND {answer_lang} != ""'
            ' ORDER BY RANDOM() LIMIT 1',
            (difficulty,)
        ).fetchone()
    except sqlite3.OperationalError:
        row = None
    finally:
        conn.close()
    if not row:
        return None
    return {'word': row[0], 'meaning': row[1] or '', 'difficulty': row[2]}


def init_db():
    """users 테이블 생성 및 vocabulary에 ar 컬럼 추가."""
    db = sqlite3.connect(DATABASE)
    db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            wins          INTEGER DEFAULT 0,
            losses        INTEGER DEFAULT 0,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    try:
        db.execute('ALTER TABLE vocabulary ADD COLUMN ar TEXT')
    except sqlite3.OperationalError:
        pass  # column already exists
    db.commit()
    db.close()


# ── REST 라우트 ───────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/get_words')
def get_words():
    difficulty = request.args.get('difficulty', 1, type=int)
    q_lang = request.args.get('question_lang', 'en').strip().lower()
    a_lang = request.args.get('answer_lang', 'ko').strip().lower()
    limit  = min(request.args.get('limit', 20, type=int), 100)
    offset = request.args.get('offset', 0, type=int)

    if q_lang not in VALID_LANGS: q_lang = 'en'
    if a_lang not in VALID_LANGS: a_lang = 'ko'
    if difficulty not in (1, 2, 3): difficulty = 1

    db = get_db()
    try:
        rows = db.execute(
            f'SELECT en, {q_lang}, {a_lang}, level FROM vocabulary'
            ' WHERE level = ? ORDER BY RANDOM() LIMIT ? OFFSET ?',
            (difficulty, limit, offset)
        ).fetchall()
    except sqlite3.OperationalError as e:
        return jsonify({'error': str(e)}), 400

    words = [
        {'word': r[0], 'q': r[1], 'a': r[2], 'level': r[3]}
        for r in rows if r[1] and r[2]
    ]
    return jsonify(words)


@app.route('/api/words/random')
def api_words_random():
    """프론트엔드 호환 라우트 — { word, meaning, difficulty }"""
    difficulty = request.args.get('difficulty', 1, type=int)
    if difficulty not in (1, 2, 3):
        difficulty = 1
    hint_lang   = request.args.get('question_lang', 'ko').strip().lower()
    answer_lang = request.args.get('answer_lang', 'en').strip().lower()
    if hint_lang not in VALID_LANGS:
        hint_lang = 'ko'
    if answer_lang not in VALID_LANGS:
        answer_lang = 'en'

    word = _db_word(difficulty, hint_lang, answer_lang)
    if not word:
        return jsonify({'error': 'no word found'}), 404
    return jsonify(word)


@app.route('/<path:path>')
def static_files(path):
    full = os.path.join(app.static_folder, path)
    if os.path.exists(full):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')


# ── 인메모리 룸 상태 ─────────────────────────────────────────
from app.game.room_manager import room_manager   # noqa: E402  (pure Python, no SQLAlchemy)
from app.game.baseball import GameState           # noqa: E402


def _offense_defense(code: str):
    """현재 이닝 half 기준으로 (offense_sid, defense_sid) 반환."""
    game    = room_manager.get_game(code)
    players = room_manager.get_players(code)
    if not game or len(players) < 2:
        return None, None
    off_team = game.half                     # 'top' | 'bottom'
    def_team = 'bottom' if off_team == 'top' else 'top'
    off = next((p['sid'] for p in players if p['team'] == off_team), None)
    dfn = next((p['sid'] for p in players if p['team'] == def_team), None)
    return off, dfn


def _emit_select_difficulty(code: str):
    """수비팀에게 난이도 선택 요청."""
    _, defense_sid = _offense_defense(code)
    emit('state:select_difficulty', {
        'defense_sid': defense_sid,
        'game_state':  room_manager.get_game(code).to_dict(),
    }, to=code)


def _emit_new_word(code: str, difficulty: int, hint_lang: str = 'ko', answer_lang: str = 'en'):
    """words.db에서 단어 조회 후 state:new_word 브로드캐스트."""
    word = _db_word(difficulty, hint_lang, answer_lang)
    if not word:
        emit('state:error', {'message': '단어 데이터를 불러올 수 없습니다'}, to=code)
        return
    room_manager.set_current_word(code, word)
    offense_sid, defense_sid = _offense_defense(code)
    emit('state:new_word', {
        'word':         word['word'],
        'meaning':      word['meaning'],    # 힌트 (hint_lang)
        'difficulty':   word['difficulty'],
        'offense_sid':  offense_sid,
        'defense_sid':  defense_sid,
        'offense_team': room_manager.get_game(code).half,
        'game_state':   room_manager.get_game(code).to_dict(),
    }, to=code)


# ── 소켓 이벤트 핸들러 ───────────────────────────────────────

@socketio.on('connect')
def on_connect():
    pass


@socketio.on('disconnect')
def on_disconnect():
    code = room_manager.find_room_by_sid(request.sid)
    if code:
        room_manager.leave_room(request.sid)
        leave_room(code)
        emit('state:room_update', {
            'code':    code,
            'players': room_manager.get_players(code),
        }, to=code)


@socketio.on('action:create_room')
def on_create_room(data):
    data     = data or {}
    username = data.get('username') or 'Guest'
    innings  = int(data.get('innings') or 9)
    code     = room_manager.create_room(request.sid, username)
    join_room(code)
    emit('state:room_created', {'code': code, 'username': username})
    emit('state:room_update',  {'code': code, 'players': room_manager.get_players(code)}, to=code)


@socketio.on('action:join_room')
def on_join_room(data):
    data     = data or {}
    code     = (data.get('code') or '').upper().strip()
    username = data.get('username') or 'Guest'

    if not room_manager.join_room(code, request.sid, username):
        emit('state:error', {'message': '방을 찾을 수 없거나 이미 가득 찼습니다'})
        return

    join_room(code)
    emit('state:room_joined',  {'code': code, 'username': username})
    emit('state:room_update',  {'code': code, 'players': room_manager.get_players(code)}, to=code)


@socketio.on('action:leave_room')
def on_leave_room(data):
    code = room_manager.find_room_by_sid(request.sid)
    if code:
        room_manager.leave_room(request.sid)
        leave_room(code)
        emit('state:room_update', {
            'code':    code,
            'players': room_manager.get_players(code),
        }, to=code)


@socketio.on('action:ready')
def on_ready(data):
    data        = data or {}
    hint_lang   = data.get('hintLang', 'ko')
    answer_lang = data.get('answerLang', 'en')
    code        = room_manager.find_room_by_sid(request.sid)
    if not code:
        return

    # 룸에 언어 설정 저장 (양쪽 중 마지막이 덮어씀 — 동일 설정 가정)
    room = room_manager.get_room(code)
    if room is not None:
        room['hint_lang']   = hint_lang
        room['answer_lang'] = answer_lang

    both_ready = room_manager.set_ready(code, request.sid)
    emit('state:player_ready', {'sid': request.sid}, to=code)

    if both_ready:
        room_manager.start_game(code)
        emit('state:game_start', {'players': room_manager.get_players(code)}, to=code)
        # 게임 시작 직후 수비팀이 난이도 선택
        _emit_select_difficulty(code)


@socketio.on('action:select_difficulty')
def on_select_difficulty(data):
    """수비팀이 난이도 선택 → 공격팀에게 새 단어 전송."""
    data       = data or {}
    difficulty = int(data.get('difficulty') or 1)
    if difficulty not in (1, 2, 3):
        difficulty = 1
    code = room_manager.find_room_by_sid(request.sid)
    if not code or not room_manager.get_game(code):
        return
    room        = room_manager.get_room(code) or {}
    hint_lang   = room.get('hint_lang',   data.get('hintLang',   'ko'))
    answer_lang = room.get('answer_lang', data.get('answerLang', 'en'))
    _emit_new_word(code, difficulty, hint_lang, answer_lang)


@socketio.on('action:answer')
def on_answer(data):
    data = data or {}
    code = room_manager.find_room_by_sid(request.sid)
    if not code:
        return

    game         = room_manager.get_game(code)
    current_word = room_manager.get_current_word(code)
    if not game or not current_word or game.game_over:
        return

    user_answer = (data.get('answer') or '').strip().lower()
    word_str    = current_word['word'].lower()
    difficulty  = current_word.get('difficulty', 1)

    # 퍼즐 정답 = 영어 철자 그대로 (한국어 뜻이 아님)
    is_correct = (user_answer == word_str)

    if is_correct:
        time_left = int(data.get('time_left') or 0)
        if time_left >= 8:          # 7초 안에 정답 → 홈런
            hit_type = 'homerun'
        else:
            hit_map = {1: 'single', 2: 'double', 3: 'triple'}
            hit_type = hit_map.get(difficulty, 'single')
        result = game.hit(hit_type)
    else:
        result = game.strike()

    result['correct_answer'] = current_word.get('meaning', word_str)
    result['word']           = current_word['word']
    result['submitted_by']   = request.sid
    emit('state:answer_result', result, to=code)

    if game.game_over:
        emit('state:game_over', {
            'score':   game.score,
            'winner':  game.winner,
            'players': room_manager.get_players(code),
        }, to=code)
    else:
        _emit_select_difficulty(code)


@socketio.on('action:use_item')
def on_use_item(data):
    data      = data or {}
    code      = room_manager.find_room_by_sid(request.sid)
    if not code:
        return
    item_type = data.get('type')

    if item_type == 'swap':
        current     = room_manager.get_current_word(code)
        diff        = current.get('difficulty', 1) if current else 1
        room        = room_manager.get_room(code) or {}
        hint_lang   = room.get('hint_lang', 'ko')
        answer_lang = room.get('answer_lang', 'en')
        _emit_new_word(code, diff, hint_lang, answer_lang)

    elif item_type == 'sabotage':
        emit('state:item_used', {
            'type':    'sabotage',
            'by_sid':  request.sid,
            'penalty': data.get('penalty', 5),
        }, to=code)


# ── 진입점 ────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    port  = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'development') != 'production'
    socketio.run(app, host='0.0.0.0', port=port, debug=debug)
