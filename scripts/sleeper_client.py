"""
sleeper_client.py
------------------
Thin wrapper around the public Sleeper API (https://docs.sleeper.com/).
No auth required.
"""

import requests
import time
from functools import lru_cache

BASE_URL = "https://api.sleeper.app/v1"


class SleeperClient:
    def __init__(self, league_id: str, sleep_between_calls: float = 0.05):
        self.league_id = league_id
        self.sleep_between_calls = sleep_between_calls
        self.session = requests.Session()

    def _get(self, path: str):
        url = f"{BASE_URL}{path}"
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        time.sleep(self.sleep_between_calls)
        return resp.json()

    def get_league(self):
        return self._get(f"/league/{self.league_id}")

    def get_rosters(self):
        return self._get(f"/league/{self.league_id}/rosters")

    def get_users(self):
        return self._get(f"/league/{self.league_id}/users")

    def get_matchups(self, week: int):
        return self._get(f"/league/{self.league_id}/matchups/{week}")

    def get_transactions(self, week: int):
        return self._get(f"/league/{self.league_id}/transactions/{week}")

    def get_traded_picks(self):
        return self._get(f"/league/{self.league_id}/traded_picks")

    def get_playoff_bracket(self, winners: bool = True):
        endpoint = "winners_bracket" if winners else "losers_bracket"
        return self._get(f"/league/{self.league_id}/{endpoint}")

    def get_previous_league_id(self):
        league = self.get_league()
        return league.get("previous_league_id")

    @staticmethod
    @lru_cache(maxsize=1)
    def get_nfl_state():
        resp = requests.get(f"{BASE_URL}/state/nfl", timeout=15)
        resp.raise_for_status()
        return resp.json()


def build_team_names(users: list, rosters: list) -> dict:
    """Returns {roster_id: team_display_name}."""
    user_map = {u["user_id"]: u for u in users}
    team_names = {}
    for r in rosters:
        owner_id = r.get("owner_id")
        roster_id = r["roster_id"]
        user = user_map.get(owner_id, {})
        metadata = user.get("metadata") or {}
        name = metadata.get("team_name") or user.get("display_name") or f"Roster {roster_id}"
        team_names[roster_id] = name
    return team_names


def build_avatars(users: list, rosters: list) -> dict:
    """Returns {roster_id: avatar_url_or_none} for use in the dashboard."""
    user_map = {u["user_id"]: u for u in users}
    avatars = {}
    for r in rosters:
        owner_id = r.get("owner_id")
        roster_id = r["roster_id"]
        user = user_map.get(owner_id, {})
        metadata = user.get("metadata") or {}
        avatar_id = metadata.get("avatar") or user.get("avatar")
        avatars[roster_id] = f"https://sleepercdn.com/avatars/thumbs/{avatar_id}" if avatar_id else None
    return avatars
