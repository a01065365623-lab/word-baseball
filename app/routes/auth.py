from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db
from ..models.user import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "username과 password가 필요합니다"}), 400
    if len(username) < 2 or len(username) > 20:
        return jsonify({"error": "username은 2~20자여야 합니다"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "이미 사용 중인 username입니다"}), 409

    user = User(username=username, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()

    session["user_id"] = user.id
    session["username"] = user.username
    return jsonify({"user": user.to_dict()}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "username 또는 password가 올바르지 않습니다"}), 401

    session["user_id"] = user.id
    session["username"] = user.username
    return jsonify({"user": user.to_dict()})


@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@auth_bp.get("/me")
def me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "로그인이 필요합니다"}), 401
    user = User.query.get(user_id)
    if not user:
        session.clear()
        return jsonify({"error": "사용자를 찾을 수 없습니다"}), 404
    return jsonify({"user": user.to_dict()})
