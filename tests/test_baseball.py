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


def test_strike_result_includes_score():
    # hit()과 동일하게 score를 포함해야 프론트가 매 스트라이크마다
    # 스코어보드를 안전하게 갱신할 수 있다
    g = make_game()
    result = g.strike()
    assert result["score"] == {"top": 0, "bottom": 0}


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


# ── 끝내기 (walk-off) ─────────────────────────────────────────────────────────

def test_walkoff_ends_game_immediately():
    g = GameState(max_innings=1)
    g.hit(HOMERUN)                   # top 1점 (1-0)
    for _ in range(9): g.strike()   # top 3아웃 → bottom of 1이닝
    tie = g.hit(HOMERUN)             # bottom 동점 (1-1) — 아직 끝내기 아님
    assert tie["walkoff"] is False
    assert g.game_over is False
    result = g.hit(HOMERUN)          # bottom 역전 (2-1) → 끝내기
    assert result["walkoff"] is True
    assert g.game_over is True
    assert g.winner == "bottom"
    assert g.outs == 0               # 3아웃을 기다리지 않고 즉시 종료


def test_no_walkoff_when_not_last_inning():
    g = GameState(max_innings=2)
    for _ in range(9): g.strike()    # top of 1이닝 종료 (0-0)
    result = g.hit(HOMERUN)          # bottom이 1점 앞서지만 마지막 이닝이 아님
    assert result["walkoff"] is False
    assert g.game_over is False


def test_no_walkoff_when_tied_or_trailing():
    g = GameState(max_innings=1)
    g.hit(HOMERUN)                    # top 1-0 (선공이 앞서 있어야 후공이 진행됨)
    for _ in range(9): g.strike()    # top of 1이닝 종료 (1-0) → 후공 진행
    result = g.hit(SINGLE)           # bottom 동점(1-1)에 불과, 역전 아님
    assert result["walkoff"] is False
    assert g.game_over is False


# ── 콜드게임 (mercy — 마지막 이닝 초 종료 시 선공이 앞서지 못하면 즉시 종료) ───
# 규칙: 마지막 이닝 초 종료 시점에 top(선공) > bottom(후공)일 때만 후공이
# 역전을 노리며 공격을 이어간다. 동점이거나 후공이 이미 앞서 있으면(top<=bottom)
# 후공 공격 없이 즉시 종료한다.

def test_mercy_ends_game_when_bottom_already_leading():
    g = GameState(max_innings=2)
    for _ in range(9): g.strike()    # top of 1이닝 종료 (0-0)
    g.hit(HOMERUN)                    # bottom 1-0
    g.hit(HOMERUN)                    # bottom 2-0
    for _ in range(9): g.strike()    # bottom of 1이닝 종료 → 2이닝(마지막) top 시작
    assert g.inning == 2
    assert g.half == "top"
    assert g.game_over is False

    result = None
    for _ in range(9):
        result = g.strike()          # 2이닝(마지막) top 3아웃 — bottom이 이미 앞서 있음
    assert result["mercy"] is True
    assert g.game_over is True
    assert g.winner == "bottom"
    assert g.half == "top"           # bottom of 2이닝은 진행되지 않음
    assert g.outs == 0


def test_mercy_ends_game_when_tied():
    g = GameState(max_innings=1)
    result = None
    for _ in range(9):
        result = g.strike()          # top of 1이닝 (0-0) 종료 — 동점
    assert result["mercy"] is True
    assert g.game_over is True
    assert g.winner == "tie"
    assert g.half == "top"           # 동점이어도 후공 공격은 진행되지 않음


def test_no_mercy_when_top_is_leading():
    g = GameState(max_innings=1)
    g.hit(HOMERUN)                   # top 1-0
    result = None
    for _ in range(9):
        result = g.strike()          # top of 1이닝 종료 — top이 앞선 상태(1-0)
    assert result["mercy"] is False
    assert g.game_over is False
    assert g.half == "bottom"        # top이 앞서 있으므로 후공이 역전을 노리며 진행


def test_no_mercy_when_not_last_inning():
    g = GameState(max_innings=2)
    for _ in range(9): g.strike()    # top of 1이닝 종료 (0-0)
    g.hit(HOMERUN)                    # bottom 1-0
    g.hit(HOMERUN)                    # bottom 2-0
    result = None
    for _ in range(9):
        result = g.strike()          # bottom of 1이닝 종료 → 2이닝 시작 (마지막 이닝 아님)
    assert result["mercy"] is False
    assert g.game_over is False
    assert g.inning == 2
    assert g.half == "top"
