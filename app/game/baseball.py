"""
Baseball rules engine — pure Python, no Flask dependency.

용어 정리
---------
half  : 'top'  = 공격팀(원정), 'bottom' = 수비팀(홈)
bases : [1루, 2루, 3루] — True 이면 주자 있음
inning: 1 ~ max_innings (기본 9이닝)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ─── hit type 상수 ────────────────────────────────────────────────────────────
SINGLE   = "single"
DOUBLE   = "double"
TRIPLE   = "triple"
HOMERUN  = "homerun"

HIT_ADVANCES = {SINGLE: 1, DOUBLE: 2, TRIPLE: 3, HOMERUN: 4}


@dataclass
class GameState:
    max_innings: int = 9
    inning: int = 1
    half: str = "top"          # 'top' | 'bottom'
    outs: int = 0
    strikes: int = 0
    balls: int = 0
    bases: list = field(default_factory=lambda: [False, False, False])
    score: dict = field(default_factory=lambda: {"top": 0, "bottom": 0})
    game_over: bool = False
    winner: Optional[str] = None   # 'top' | 'bottom' | 'tie'

    # ── public API ────────────────────────────────────────────────────────────

    def hit(self, hit_type: str) -> dict:
        """정답 → 타격 결과 처리. runs scored 반환."""
        advances = HIT_ADVANCES.get(hit_type, 1)
        runs = self._advance_runners(advances)
        self._reset_count()
        return {
            "event": "hit",
            "hit_type": hit_type,
            "runs": runs,
            "bases": list(self.bases),
            "score": dict(self.score),
            "game_over": self.game_over,
            "winner": self.winner,
        }

    def strike(self) -> dict:
        """오답 → 스트라이크 처리. 3 스트라이크 시 아웃."""
        self.strikes += 1
        result: dict = {"event": "strike", "strikes": self.strikes}
        if self.strikes >= 3:
            result["out"] = True
            result.update(self._record_out())
        result.update({"game_over": self.game_over, "winner": self.winner})
        return result

    def ball(self) -> dict:
        """볼 처리. 4 볼 시 볼넷(1루 진루)."""
        self.balls += 1
        result: dict = {"event": "ball", "balls": self.balls}
        if self.balls >= 4:
            runs = self._walk()
            self._reset_count()
            result["walk"] = True
            result["runs"] = runs
            result["bases"] = list(self.bases)
            result["score"] = dict(self.score)
        result.update({"game_over": self.game_over, "winner": self.winner})
        return result

    def to_dict(self) -> dict:
        return {
            "inning": self.inning,
            "half": self.half,
            "outs": self.outs,
            "strikes": self.strikes,
            "balls": self.balls,
            "bases": list(self.bases),
            "score": dict(self.score),
            "game_over": self.game_over,
            "winner": self.winner,
        }

    # ── internal helpers ──────────────────────────────────────────────────────

    def _advance_runners(self, advances: int) -> int:
        """타자 포함 모든 주자를 advances 루씩 진루. 홈인 수 반환."""
        runs = 0
        new_bases = [False, False, False]

        # 타자는 -1 위치에서 출발
        positions = [-1] + [i for i, occ in enumerate(self.bases) if occ]

        for pos in positions:
            new_pos = pos + advances
            if new_pos >= 3:        # 홈 통과 → 득점
                runs += 1
            else:
                new_bases[new_pos] = True

        self.bases = new_bases
        self.score[self.half] += runs
        return runs

    def _walk(self) -> int:
        """볼넷: 타자 1루. 만루 시 강제 진루로 득점 발생."""
        runs = 0
        b = list(self.bases)

        if b[0] and b[1] and b[2]:   # 만루
            runs = 1
            # 모든 루에 주자 유지 (3루 주자 홈인)
            b = [True, True, True]
        elif b[0] and b[1]:          # 1·2루
            b[2] = True              # 2루 → 3루, 1루 → 2루, 타자 → 1루
        elif b[0]:                   # 1루만
            b[1] = True              # 1루 → 2루, 타자 → 1루
        else:
            b[0] = True              # 타자 → 1루

        self.bases = b
        self.score[self.half] += runs
        return runs

    def _reset_count(self):
        self.strikes = 0
        self.balls = 0

    def _record_out(self) -> dict:
        self.outs += 1
        self._reset_count()
        result: dict = {"outs": self.outs}
        if self.outs >= 3:
            result["inning_change"] = True
            self._next_half_inning()
        return result

    def _next_half_inning(self):
        self.outs = 0
        self.strikes = 0
        self.balls = 0
        self.bases = [False, False, False]

        if self.half == "top":
            self.half = "bottom"
        else:
            self.half = "top"
            self.inning += 1
            if self.inning > self.max_innings:
                self._end_game()

    def _end_game(self):
        self.game_over = True
        t = self.score["top"]
        b = self.score["bottom"]
        if t > b:
            self.winner = "top"
        elif b > t:
            self.winner = "bottom"
        else:
            self.winner = "tie"
