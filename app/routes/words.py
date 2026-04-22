from flask import Blueprint, request, jsonify
from ..game.word_engine import word_engine

words_bp = Blueprint("words", __name__)


@words_bp.get("/random")
def random_word():
    """난이도별 랜덤 단어 반환. ?difficulty=1|2|3"""
    difficulty = request.args.get("difficulty", type=int)
    word = word_engine.get_random_word(difficulty)
    if not word:
        return jsonify({"error": "단어 데이터가 없습니다"}), 404
    # 클라이언트에게 meaning 은 숨기고 word 와 difficulty 만 전달
    return jsonify({
        "id": word.get("id"),
        "word": word["word"],
        "meaning": word.get("meaning", ""),
        "difficulty": word.get("difficulty", 1),
        "category": word.get("category", "general"),
    })
