"""
analytics.py
------------
Pure computation functions: power rankings, all-play luck index, actual records.
No printing, no I/O — generate_data.py consumes these and writes JSON.
"""

from collections import defaultdict


def gather_weekly_scores(client, through_week: int):
    """Returns ({roster_id: [scores...]}, played_weeks)."""
    scores = defaultdict(list)
    played_weeks = 0

    for week in range(1, through_week + 1):
        matchups = client.get_matchups(week)
        if not matchups or all(m.get("points", 0) == 0 for m in matchups):
            break
        played_weeks += 1
        for m in matchups:
            scores[m["roster_id"]].append(m.get("points", 0.0))

    return scores, played_weeks


def all_play_record(scores: dict, week_index: int):
    week_scores = {rid: s[week_index] for rid, s in scores.items() if len(s) > week_index}
    record = {}
    for rid, my_score in week_scores.items():
        w = l = t = 0
        for other_rid, other_score in week_scores.items():
            if other_rid == rid:
                continue
            if my_score > other_score:
                w += 1
            elif my_score < other_score:
                l += 1
            else:
                t += 1
        record[rid] = (w, l, t)
    return record


def compute_luck_index(scores: dict, played_weeks: int):
    totals = defaultdict(lambda: {"ap_w": 0, "ap_l": 0, "ap_t": 0})

    for week_index in range(played_weeks):
        week_record = all_play_record(scores, week_index)
        for rid, (w, l, t) in week_record.items():
            totals[rid]["ap_w"] += w
            totals[rid]["ap_l"] += l
            totals[rid]["ap_t"] += t

    results = {}
    for rid, rec in totals.items():
        total_games = rec["ap_w"] + rec["ap_l"] + rec["ap_t"]
        pct = (rec["ap_w"] + 0.5 * rec["ap_t"]) / total_games if total_games else 0
        results[rid] = {
            "all_play_wins": rec["ap_w"],
            "all_play_losses": rec["ap_l"],
            "all_play_ties": rec["ap_t"],
            "all_play_pct": round(pct, 3),
        }
    return results


def compute_actual_records(client, through_week: int):
    records = defaultdict(lambda: {"wins": 0, "losses": 0, "ties": 0, "points_for": 0.0, "points_against": 0.0})

    for week in range(1, through_week + 1):
        matchups = client.get_matchups(week)
        if not matchups or all(m.get("points", 0) == 0 for m in matchups):
            break

        by_matchup = defaultdict(list)
        for m in matchups:
            by_matchup[m["matchup_id"]].append(m)

        for pair in by_matchup.values():
            if len(pair) != 2:
                continue
            a, b = pair
            records[a["roster_id"]]["points_for"] += a["points"]
            records[a["roster_id"]]["points_against"] += b["points"]
            records[b["roster_id"]]["points_for"] += b["points"]
            records[b["roster_id"]]["points_against"] += a["points"]

            if a["points"] > b["points"]:
                records[a["roster_id"]]["wins"] += 1
                records[b["roster_id"]]["losses"] += 1
            elif b["points"] > a["points"]:
                records[b["roster_id"]]["wins"] += 1
                records[a["roster_id"]]["losses"] += 1
            else:
                records[a["roster_id"]]["ties"] += 1
                records[b["roster_id"]]["ties"] += 1

    return records


def compute_power_rankings(scores: dict, actual_records: dict, luck: dict):
    roster_ids = list(scores.keys())
    max_pf = max((actual_records[rid]["points_for"] for rid in roster_ids), default=1) or 1

    rankings = []
    for rid in roster_ids:
        recent = scores[rid][-3:] if len(scores[rid]) >= 3 else scores[rid]
        recent_avg = sum(recent) / len(recent) if recent else 0
        ap_pct = luck[rid]["all_play_pct"] if rid in luck else 0
        pf_norm = actual_records[rid]["points_for"] / max_pf if max_pf else 0

        composite = (0.5 * recent_avg) + (30 * ap_pct) + (20 * pf_norm)

        rankings.append({
            "roster_id": rid,
            "composite_score": round(composite, 2),
            "recent_avg_3wk": round(recent_avg, 1),
            "all_play_pct": ap_pct,
            "wins": actual_records[rid]["wins"],
            "losses": actual_records[rid]["losses"],
            "ties": actual_records[rid]["ties"],
            "points_for": round(actual_records[rid]["points_for"], 1),
            "points_against": round(actual_records[rid]["points_against"], 1),
        })

    rankings.sort(key=lambda x: x["composite_score"], reverse=True)
    for i, r in enumerate(rankings, 1):
        r["rank"] = i
    return rankings


def compute_luck_delta(actual_records: dict, luck: dict):
    deltas = {}
    for rid, rec in actual_records.items():
        total = rec["wins"] + rec["losses"] + rec["ties"]
        actual_pct = (rec["wins"] + 0.5 * rec["ties"]) / total if total else 0
        ap_pct = luck.get(rid, {}).get("all_play_pct", 0)
        deltas[rid] = round(actual_pct - ap_pct, 3)
    return deltas
