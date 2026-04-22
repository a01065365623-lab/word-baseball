"""
RoomManager — 인메모리 게임 룸 상태 관리 (싱글톤).

각 룸은 다음 정보를 유지:
  players   : [{'sid': str, 'username': str, 'team': 'top'|'bottom'}]
  game      : GameState 인스턴스
  current_word : 현재 출제된 단어 dict
  ready_set : 준비 완료된 sid 집합
"""

from __future__ import annotations
import random
import string
from typing import Optional

from .baseball import GameState


class RoomManager:
    def __init__(self):
        # code → room_data dict
        self._rooms: dict[str, dict] = {}

    # ── 룸 생성 / 참가 ─────────────────────────────────────────────────────────

    def create_room(self, host_sid: str, username: str) -> str:
        """새 룸 생성. 생성된 룸 코드 반환."""
        code = self._unique_code()
        self._rooms[code] = {
            "players": [{"sid": host_sid, "username": username, "team": "top"}],
            "game": None,
            "current_word": None,
            "ready_set": set(),
        }
        return code

    def join_room(self, code: str, sid: str, username: str) -> bool:
        """룸 참가. 성공 여부 반환. 2인 초과 입장 불가."""
        room = self._rooms.get(code)
        if not room:
            return False
        if len(room["players"]) >= 2:
            return False
        room["players"].append({"sid": sid, "username": username, "team": "bottom"})
        return True

    def leave_room(self, sid: str) -> Optional[str]:
        """플레이어 퇴장. 룸 코드 반환 (없으면 None)."""
        for code, room in list(self._rooms.items()):
            room["players"] = [p for p in room["players"] if p["sid"] != sid]
            room["ready_set"].discard(sid)
            if not room["players"]:
                del self._rooms[code]
            return code
        return None

    # ── 게임 흐름 ──────────────────────────────────────────────────────────────

    def set_ready(self, code: str, sid: str) -> bool:
        """준비 완료 등록. 양쪽 모두 준비되면 True 반환."""
        room = self._rooms.get(code)
        if not room:
            return False
        room["ready_set"].add(sid)
        return len(room["ready_set"]) == 2

    def start_game(self, code: str):
        """게임 상태 초기화."""
        room = self._rooms.get(code)
        if room:
            room["game"] = GameState()
            room["ready_set"] = set()

    def set_current_word(self, code: str, word: dict):
        room = self._rooms.get(code)
        if room:
            room["current_word"] = word

    def get_current_word(self, code: str) -> Optional[dict]:
        room = self._rooms.get(code)
        return room["current_word"] if room else None

    def get_game(self, code: str) -> Optional[GameState]:
        room = self._rooms.get(code)
        return room["game"] if room else None

    def get_players(self, code: str) -> list:
        room = self._rooms.get(code)
        return room["players"] if room else []

    def get_room(self, code: str) -> Optional[dict]:
        return self._rooms.get(code)

    def find_room_by_sid(self, sid: str) -> Optional[str]:
        """sid 로 룸 코드 찾기."""
        for code, room in self._rooms.items():
            if any(p["sid"] == sid for p in room["players"]):
                return code
        return None

    def list_waiting_rooms(self) -> list[dict]:
        result = []
        for code, room in self._rooms.items():
            if len(room["players"]) == 1 and room["game"] is None:
                host = room["players"][0]["username"]
                result.append({"code": code, "host": host})
        return result

    # ── 내부 ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _unique_code() -> str:
        return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


# 싱글톤
room_manager = RoomManager()
