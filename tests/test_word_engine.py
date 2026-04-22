import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.game.word_engine import WordEngine


@pytest.fixture
def engine():
    e = WordEngine()
    return e


def test_load_json_words(engine):
    assert len(engine._json_words) > 0


def test_get_random_word_returns_word(engine):
    word = engine.get_random_word()
    assert word is not None
    assert "word" in word
    assert "meaning" in word


def test_get_random_word_by_difficulty(engine):
    word = engine.get_random_word(difficulty=1)
    assert word is not None
    assert word.get("difficulty") == 1


def test_check_answer_correct(engine):
    # apple → 사과 (difficulty 1 → homerun)
    result = engine.check_answer("apple", "사과", difficulty=1)
    assert result == "homerun"


def test_check_answer_wrong(engine):
    result = engine.check_answer("apple", "바나나", difficulty=1)
    assert result == "strike"


def test_check_answer_case_insensitive(engine):
    result = engine.check_answer("Apple", "사과", difficulty=1)
    assert result == "homerun"


def test_check_answer_slash_meaning(engine):
    # abandon → 버리다/포기하다
    result1 = engine.check_answer("abandon", "버리다", difficulty=2)
    result2 = engine.check_answer("abandon", "포기하다", difficulty=2)
    assert result1 == "double"
    assert result2 == "double"


def test_check_answer_empty_returns_strike(engine):
    result = engine.check_answer("apple", "", difficulty=1)
    assert result == "strike"


def test_difficulty_hit_mapping(engine):
    assert engine.check_answer("apple", "사과", difficulty=1) == "homerun"
    assert engine.check_answer("ancient", "고대의", difficulty=2) == "double"
    assert engine.check_answer("ambiguous", "모호한", difficulty=3) == "single"
