"""
generate_data.py
-----------------
The single entrypoint the GitHub Action runs on a schedule.

It pulls live data from Sleeper, computes power rankings + luck index,
and writes JSON files into docs/data/ for the static site to consume.

Usage:
    python3 scripts/generate_data.py

Configure via environment variable LEAGUE_ID, or edit DEFAULT_LEAGUE_ID below.
"""

import os
import json
import sys
from datetime import datetime, timezone

from sleeper_client import SleeperClient, build_team_names, build_avatars
from analytics import (
    gather_weekly_scores,
    compute_luck_index,
    compute_actual_records,
    compute_power_rankings,
    compute_luck_delta,
)

DEFAULT_LEAGUE_ID = "1389378221123833856"  # Everest+
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "data")


def determine_current_week(client: SleeperClient) -> int:
    """
    Uses Sleeper's global NFL state to figure out the current week, then
    backs off by checking which weeks actually have scores (in case the
    current week hasn't kicked off yet).
    """
    try:
        state = client.get_nfl_state()
        week = state.get("week", 1)
        # NFL state week can be ahead of what's playable; cap sensibly.
        return max(1, min(week, 18))
    except Exception as e:
        print(f"Warning: couldn't fetch NFL state ({e}), defaulting to week 18 scan", file=sys.stderr)
        return 18


def main():
    league_id = os.environ.get("LEAGUE_ID", DEFAULT_LEAGUE_ID)
    client = SleeperClient(league_id)

    print(f"Fetching league info for {league_id}...")
    league = client.get_league()
    users = client.get_users()
    rosters = client.get_rosters()
    names = build_team_names(users, rosters)
    avatars = build_avatars(users, rosters)

    current_week_guess = determine_current_week(client)
    print(f"Scanning through week {current_week_guess} for played games...")

    scores, played_weeks = gather_weekly_scores(client, current_week_guess)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if played_weeks == 0:
        print("No completed weeks yet. Writing placeholder data.")
        payload = {
            "league_name": league.get("name"),
            "season": league.get("season"),
            "played_weeks": 0,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "preseason",
            "rankings": [],
            "luck": [],
        }
        with open(os.path.join(OUTPUT_DIR, "rankings.json"), "w") as f:
            json.dump(payload, f, indent=2)
        print("Done (preseason placeholder written).")
        return

    actual = compute_actual_records(client, played_weeks)
    luck = compute_luck_index(scores, played_weeks)
    deltas = compute_luck_delta(actual, luck)
    rankings = compute_power_rankings(scores, actual, luck)

    # Attach names/avatars/luck delta to each ranking entry for the front end
    for r in rankings:
        rid = r["roster_id"]
        r["team_name"] = names.get(rid, f"Roster {rid}")
        r["avatar_url"] = avatars.get(rid)
        r["luck_delta"] = deltas.get(rid, 0)

    luck_leaderboard = sorted(
        [
            {
                "roster_id": rid,
                "team_name": names.get(rid, f"Roster {rid}"),
                "avatar_url": avatars.get(rid),
                "actual_record": f"{actual[rid]['wins']}-{actual[rid]['losses']}"
                + (f"-{actual[rid]['ties']}" if actual[rid]["ties"] else ""),
                "all_play_pct": luck[rid]["all_play_pct"],
                "luck_delta": deltas[rid],
            }
            for rid in actual.keys()
        ],
        key=lambda x: x["luck_delta"],
        reverse=True,
    )

    payload = {
        "league_name": league.get("name"),
        "season": league.get("season"),
        "played_weeks": played_weeks,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
        "rankings": rankings,
        "luck": luck_leaderboard,
    }

    out_path = os.path.join(OUTPUT_DIR, "rankings.json")
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Wrote {out_path} — {len(rankings)} teams, through week {played_weeks}.")


if __name__ == "__main__":
    main()
