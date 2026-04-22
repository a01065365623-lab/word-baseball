"""
Word engine — 단어 출제 및 정답 채점.

채점 기준
---------
- 정답(대소문자 무시) → 난이도에 따라 hit type 결정
  difficulty 1: HOMERUN
  difficulty 2: DOUBLE
  difficulty 3: SINGLE
- 오답 → 'strike'
"""

from __future__ import annotations
import json
import os
import random
from typing import Optional


# hit type 상수 (baseball.py 와 동일)
HOMERUN = "homerun"
DOUBLE  = "double"
SINGLE  = "single"

DIFFICULTY_HIT = {1: HOMERUN, 2: DOUBLE, 3: SINGLE}

# 난이도별 단어 글자 수 범위 (inclusive)
LENGTH_RANGE: dict[int, tuple[int, int]] = {
    1: (4, 5),
    2: (5, 7),
    3: (6, 9),
}


class WordEngine:
    """
    단어 데이터는 두 가지 소스에서 로드:
    1. SQLite DB (Word 모델) — 운영 환경
    2. data/words.json      — DB 비어 있을 때 폴백
    """

    def __init__(self):
        self._json_words: list[dict] = []
        self._load_json()

    # ── public API ─────────────────────────────────────────────────────────────

    def get_random_word(self, difficulty: Optional[int] = None) -> Optional[dict]:
        """DB 우선, 없으면 JSON에서 랜덤 단어 반환. 난이도별 글자 수 범위 적용."""
        min_len, max_len = LENGTH_RANGE.get(difficulty, (1, 99)) if difficulty else (1, 99)

        try:
            from ..models.word import Word
            query = Word.query
            if difficulty:
                query = query.filter_by(difficulty=difficulty)
            words = query.all()
            words = [w for w in words if min_len <= len(w.word) <= max_len]
            if words:
                return random.choice(words).to_dict()
        except Exception:
            pass

        # JSON 폴백
        pool = self._json_words
        if difficulty:
            pool = [w for w in pool if w.get("difficulty") == difficulty]
        pool = [w for w in pool if min_len <= len(w.get("word", "")) <= max_len]
        if not pool:
            # 글자 수 조건만 완화해서 재시도
            pool = [w for w in self._json_words if min_len <= len(w.get("word", "")) <= max_len]
        return random.choice(pool) if pool else None

    def check_answer(self, word: str, user_answer: str, difficulty: int = 1) -> str:
        """
        user_answer 가 word 의 뜻(meaning)과 일치하면 hit type,
        틀리면 'strike' 반환.

        word     : 영단어
        user_answer : 사용자가 입력한 한국어 뜻
        difficulty  : 1~3
        """
        if not word or not user_answer:
            return "strike"

        answer_clean = user_answer.strip().lower()

        # DB에서 해당 단어의 정답 목록 조회
        try:
            from ..models.word import Word
            record = Word.query.filter(
                Word.word.ilike(word)
            ).first()
            if record:
                correct = record.meaning.strip().lower()
                if self._is_correct(answer_clean, correct):
                    return DIFFICULTY_HIT.get(record.difficulty, SINGLE)
                return "strike"
        except Exception:
            pass

        # JSON 폴백
        for w in self._json_words:
            if w["word"].lower() == word.lower():
                correct = w["meaning"].strip().lower()
                if self._is_correct(answer_clean, correct):
                    return DIFFICULTY_HIT.get(w.get("difficulty", 1), SINGLE)
                return "strike"

        return "strike"

    # ── helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _is_correct(answer: str, correct: str) -> bool:
        """정답 판별: 완전 일치 또는 핵심 단어 포함."""
        if answer == correct:
            return True
        # 복수 뜻이 '/' 로 구분된 경우 각각 비교
        for part in correct.split("/"):
            if answer == part.strip():
                return True
        return False

    def _load_json(self):
        base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        path = os.path.join(base, "data", "words.json")
        try:
            with open(path, encoding="utf-8") as f:
                self._json_words = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._json_words = []


# 싱글톤
word_engine = WordEngine()
