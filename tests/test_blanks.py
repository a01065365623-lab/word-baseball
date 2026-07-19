"""
app.py(리포지토리 루트 스크립트)의 빈칸 개수 규칙을 검증한다.

주의: 프로젝트에는 app.py(스크립트)와 app/(패키지)가 동시에 존재해서
`import app`은 app/__init__.py를 가져온다. app.py 자체를 테스트하려면
importlib로 파일 경로를 직접 지정해 로드해야 한다.
"""
import importlib.util
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def app_root():
    spec = importlib.util.spec_from_file_location("app_root_script", os.path.join(_ROOT, "app.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── hintMode 매핑 ──────────────────────────────────────────────────────────

def test_hint_mode_aa_is_2(app_root):
    assert app_root._hint_mode_for_difficulty(1) == 2


def test_hint_mode_minor_is_1(app_root):
    assert app_root._hint_mode_for_difficulty(2) == 1


def test_hint_mode_major_is_0(app_root):
    assert app_root._hint_mode_for_difficulty(3) == 0


# ── hintMode별 빈칸 개수 ───────────────────────────────────────────────────

def test_blanks_hint_mode_2_is_3(app_root):
    assert app_root._pick_blanks("abandon", 1) == 3


def test_blanks_hint_mode_1_is_4(app_root):
    assert app_root._pick_blanks("abandon", 2) == 4


def test_blanks_hint_mode_0_is_6(app_root):
    assert app_root._pick_blanks("abandon", 3) == 6


# ── 단어 길이보다 빈칸이 많을 때 clamp ──────────────────────────────────────

def test_blanks_clamped_to_word_length_when_shorter(app_root):
    # hintMode 0 → 기본 6칸이지만 4글자 단어라 전체(4)가 빈칸이 되어야 함
    assert app_root._pick_blanks("word", 3) == 4


def test_blanks_clamped_for_very_short_word(app_root):
    assert app_root._pick_blanks("ab", 3) == 2


def test_blanks_never_exceeds_word_length(app_root):
    for difficulty in (1, 2, 3):
        for word in ("a", "ab", "abc", "abcd", "abcde", "abcdefghij"):
            blanks = app_root._pick_blanks(word, difficulty)
            assert 1 <= blanks <= len(word)


# ── 빈칸 개수 → 타격 결과 (시간 기준은 기존 그대로 유지) ────────────────────

def test_hit_type_3_blanks_single(app_root):
    assert app_root._hit_type_for_blanks(3, 10) == "single"


def test_hit_type_4_blanks_double(app_root):
    assert app_root._hit_type_for_blanks(4, 10) == "double"


def test_hit_type_6_blanks_homerun_when_time_left_7_or_more(app_root):
    assert app_root._hit_type_for_blanks(6, 7) == "homerun"


def test_hit_type_6_blanks_triple_when_time_left_under_7(app_root):
    assert app_root._hit_type_for_blanks(6, 6) == "triple"
