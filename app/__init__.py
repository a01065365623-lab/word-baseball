import os
from flask import Flask, send_from_directory
from .extensions import db, socketio
from .config import config


def create_app(env: str = None) -> Flask:
    app = Flask(__name__, static_folder="static", static_url_path="")

    # 설정 로드
    env = env or os.environ.get("FLASK_ENV", "default")
    app.config.from_object(config.get(env, config["default"]))

    # 익스텐션 초기화
    db.init_app(app)
    socketio.init_app(
        app,
        cors_allowed_origins=app.config["CORS_ORIGINS"],
        async_mode="eventlet",
    )

    with app.app_context():
        # 모델 임포트 → 테이블 자동 생성
        from .models import User, Room, Word  # noqa: F401
        db.create_all()

        # 단어 데이터 시드 (DB가 비어 있을 때만)
        _seed_words()

    # 블루프린트 등록
    from .routes.auth import auth_bp
    from .routes.rooms import rooms_bp
    from .routes.words import words_bp
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(rooms_bp, url_prefix="/api/rooms")
    app.register_blueprint(words_bp, url_prefix="/api/words")

    # 소켓 핸들러 등록
    from . import sockets  # noqa: F401

    # SPA 폴백 라우트
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_spa(path: str):
        if path and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, "index.html")

    return app


def _seed_words():
    """words.json → DB 초기 적재 (Word 테이블이 비어 있을 때만)."""
    import json
    from .models.word import Word
    from .extensions import db

    if Word.query.first():
        return  # 이미 데이터 있음

    base = os.path.dirname(os.path.dirname(__file__))
    path = os.path.join(base, "data", "words.json")
    try:
        with open(path, encoding="utf-8") as f:
            words = json.load(f)
        for w in words:
            db.session.add(Word(
                word=w["word"],
                meaning=w["meaning"],
                difficulty=w.get("difficulty", 1),
                category=w.get("category", "general"),
            ))
        db.session.commit()
    except (FileNotFoundError, json.JSONDecodeError):
        pass
