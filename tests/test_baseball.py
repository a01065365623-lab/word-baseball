import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.game.baseball import GameState, SINGLE, DOUBLE, TRIPLE, HOMERUN


def make_game():
    return GameState()


# ── 기본 상태 ─────────────────────────────────────────────────────────────────

def test_initial_state():
    g = make_game()
    assert g.inning == 1
    assert g.half == "top"
    assert g.outs == 0
    assert g.strikes == 0
    assert g.balls == 0
    assert g.bases == [False, False, False]
    assert g.score == {"top": 0, "bottom": 0}
    assert g.game_over is False


# ── 스트라이크 / 아웃 ──────────────────────────────────────────────────────────

def test_three_strikes_make_out():
    g = make_game()
    g.strike()
    g.strike()
    result = g.strike()
    assert result["out"] is True
    assert g.outs == 1
    assert g.strikes == 0   # 카운트 리셋


def test_three_outs_change_half():
    g = make_game()
    for _ in range(9):   # 3아웃 × 3 (스트라이크)
        g.strike()
    assert g.half == "bottom"
    assert g.inning == 1
    assert g.outs == 0


def test_six_outs_next_inning():
    g = make_game()
    for _ in range(18):  # 6아웃
        g.strike()
    assert g.inning == 2
    assert g.half == "top"


# ── 히트 / 득점 ────────────────────────────────────────────────────────────────

def test_homerun_scores_one():
    g = make_game()
    result = g.hit(HOMERUN)
    assert result["runs"] == 1
    assert g.score["top"] == 1
    assert g.bases == [False, False, False]


def test_homerun_clears_bases():
    g = make_game()
    g.bases = [True, True, True]
    result = g.hit(HOMERUN)
    assert result["runs"] == 4
    assert g.score["top"] == 4
    assert g.bases == [False, False, False]


def test_single_advances_runner():
    g = make_game()
    g.bases = [False, False, True]   # 3루 주자
    result = g.hit(SINGLE)
    assert result["runs"] == 1       # 3루 주자 홈인
    assert g.bases[0] is True        # 타자 1루
    assert g.bases[2] is False


def test_double_advances_two():
    g = make_game()
    g.bases = [True, False, False]   # 1루 주자
    result = g.hit(DOUBLE)
    assert result["runs"] == 0
    assert g.bases[2] is True        # 1루 주자 → 3루
    assert g.bases[1] is True        # 타자 → 2루


# ── 볼넷 ──────────────────────────────────────────────────────────────────────

def test_four_balls_walk():
    g = make_game()
    g.ball(); g.ball(); g.ball()
    result = g.ball()
    assert result["walk"] is True
    assert g.bases[0] is True
    assert g.balls == 0   # 카운트 리셋


def test_walk_with_loaded_bases_scores():
    g = make_game()
    g.bases = [True, True, True]
    result = g.ball(); g.ball(); g.ball()
    result = g.ball()
    assert result["runs"] == 1
    assert g.score["top"] == 1


# ── 게임 종료 ─────────────────────────────────────────────────────────────────

def test_game_ends_after_max_innings():
    g = GameState(max_innings=1)
    # 1이닝 top 3아웃
    for _ in range(9):
        g.strike()
    # 1이닝 bottom 3아웃
    for _ in range(9):
        g.strike()
    assert g.game_over is True


def test_winner_determined():
    g = GameState(max_innings=1)
    g.hit(HOMERUN)                   # top 1점
    for _ in range(9): g.strike()   # top 3아웃
    for _ in range(9): g.strike()   # bottom 3아웃
    assert g.winner == "top"
