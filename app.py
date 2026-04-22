import os
import sqlite3
import random

from flask import Flask, g, jsonify, request, send_from_directory
from flask_socketio import SocketIO

app = Flask(__name__, static_folder='app/static', static_url_path='')
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')

socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

DATABASE = os.path.join(os.path.dirname(__file__), 'words.db')

VALID_LANGS = {
    'en', 'ko', 'ja', 'zh', 'de', 'fr', 'hi', 'es', 'pt', 'it', 'ru', 'tr', 'vi', 'ar'
}


# ── DB 연결 ────────────────────────────────────────────────────

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


def init_db():
    """users 테이블 생성 및 vocabulary 에 ar 컬럼 추가."""
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


# ── 라우트 ────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/get_words')
def get_words():
    """
    단어 목록 반환.
    Query params:
      - difficulty: 1 (beginner) | 2 (intermediate) | 3 (advanced), default 1
      - question_lang: 언어 코드 (default 'en')
      - answer_lang:   언어 코드 (default 'ko')
      - limit:  반환 개수 (default 20)
      - offset: 페이지 오프셋 (default 0)
    """
    difficulty = request.args.get('difficulty', 1, type=int)
    q_lang = request.args.get('question_lang', 'en').strip().lower()
    a_lang = request.args.get('answer_lang', 'ko').strip().lower()
    limit = min(request.args.get('limit', 20, type=int), 100)
    offset = request.args.get('offset', 0, type=int)

    if q_lang not in VALID_LANGS:
        q_lang = 'en'
    if a_lang not in VALID_LANGS:
        a_lang = 'ko'
    if difficulty not in (1, 2, 3):
        difficulty = 1

    db = get_db()
    try:
        # q_lang / a_lang 은 VALID_LANGS whitelist 통과 후 사용 → SQL injection 없음
        rows = db.execute(
            f'SELECT en, {q_lang}, {a_lang}, level FROM vocabulary'
            ' WHERE level = ? ORDER BY RANDOM() LIMIT ? OFFSET ?',
            (difficulty, limit, offset)
        ).fetchall()
    except sqlite3.OperationalError as e:
        return jsonify({'error': str(e)}), 400

    words = []
    for row in rows:
        q_val = row[1]
        a_val = row[2]
        if q_val and a_val:
            words.append({
                'word': row[0],   # 항상 영어 단어 (발음 TTS 용)
                'q': q_val,
                'a': a_val,
                'level': row[3],
            })

    return jsonify(words)


# ── 정적 파일 폴백 (SPA) ──────────────────────────────────────

@app.route('/<path:path>')
def static_files(path):
    full = os.path.join(app.static_folder, path)
    if os.path.exists(full):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')


# ── SocketIO 이벤트 (기본) ────────────────────────────────────

@socketio.on('connect')
def on_connect():
    pass


@socketio.on('disconnect')
def on_disconnect():
    pass


# ── 진입점 ────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'development') != 'production'
    socketio.run(app, host='0.0.0.0', port=port, debug=debug)
